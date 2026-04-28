"""Passive AI webcam attendance page for admins."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List

import pandas as pd
import streamlit as st

from config.settings import PASSIVE_ATTENDANCE_ENABLED
from passive_attendance.webrtc_processor import PassiveAttendanceVideoProcessor
from services.passive_attendance_service import PassiveAttendanceService
from services.student_service import StudentService
from ui.components.layout import card_container, render_info_strip, render_page_header, section_title

logger = logging.getLogger(__name__)

try:
    from streamlit_webrtc import RTCConfiguration, webrtc_streamer
except ImportError as e:
    webrtc_streamer = None
    RTCConfiguration = None
    _IMPORT_ERROR = str(e)
else:
    _IMPORT_ERROR = None


class PassiveAIAttendancePage:
    """Admin page to run passive classroom attendance monitoring."""

    def __init__(self) -> None:
        self.service = PassiveAttendanceService()
        self.student_service = StudentService()

    def render(self) -> None:
        render_page_header(
            title="Passive AI Classroom Attendance",
            subtitle="Automatic roster-aware attendance from classroom webcam without student interaction.",
            icon="📡",
        )

        render_info_strip(
            items=[
                ("Passive mode", "No student clicks or scans; detection runs continuously."),
                ("Smart validation", "Requires consecutive frames, confidence threshold, and visible duration."),
                ("Session-aware", "Attendance is marked only for active class roster students."),
            ]
        )

        if not PASSIVE_ATTENDANCE_ENABLED:
            st.warning("Passive attendance is disabled by configuration.")
            return

        self._render_session_controls()

        active_session = self.service.get_active_session()
        if not active_session:
            st.info("Start a passive class session to begin live monitoring.")
            return

        col_live, col_side = st.columns([3, 2])
        with col_live:
            with card_container():
                section_title("Live Classroom Feed", icon="🎥")
                self._render_live_monitor(active_session)

        with col_side:
            with card_container():
                section_title("Live Dashboard", icon="📊")
                self._render_live_dashboard(active_session)

    def _render_session_controls(self) -> None:
        st.markdown("### Session Controls")
        sessions = self.service.list_sessions(limit=20)
        active = self.service.get_active_session()
        students = self.student_service.get_all_students()

        col1, col2 = st.columns([2, 1])
        with col1:
            class_name = st.text_input("Class name", value="CS - Passive Session", key="passive_class_name")
            course = st.text_input("Course", value="Computer Science", key="passive_course")
            selected_students = st.multiselect(
                "Class roster students",
                options=[s["id"] for s in students],
                format_func=lambda sid: next((f"{x['name']} ({x['roll_number']})" for x in students if x["id"] == sid), str(sid)),
                key="passive_roster_selector",
            )

            c1, c2 = st.columns(2)
            with c1:
                if st.button("▶ Start Passive Session", use_container_width=True):
                    ok, msg, session_id = self.service.create_session(
                        class_name=class_name,
                        course=course,
                        camera_source="webcam",
                        created_by="admin",
                        start_time=datetime.now().isoformat(timespec="seconds"),
                        student_ids=selected_students,
                    )
                    if ok:
                        st.success(f"{msg} (ID {session_id})")
                        st.rerun()
                    else:
                        st.error(msg)

            with c2:
                if st.button("⏹ Stop Active Session", use_container_width=True):
                    ok, msg = self.service.stop_active_session()
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with col2:
            st.markdown("#### Current Session")
            if active:
                st.success(f"Active: {active.get('class_name')} (ID {active.get('id')})")
                st.caption(f"Course: {active.get('course') or 'N/A'}")
                st.caption(f"Started: {active.get('start_time') or active.get('created_at')}")
            else:
                st.info("No active session")

            if sessions:
                st.markdown("#### Recent Sessions")
                for row in sessions[:5]:
                    status = "active" if int(row.get("is_active", 0)) == 1 else "closed"
                    st.caption(f"#{row['id']} {row['class_name']} ({status})")

        st.markdown("---")

    def _render_live_monitor(self, active_session: Dict) -> None:
        if webrtc_streamer is None:
            st.error("streamlit-webrtc is not installed.")
            st.code("pip install streamlit-webrtc av", language="bash")
            if _IMPORT_ERROR:
                st.caption(_IMPORT_ERROR)
            return

        session_id = int(active_session["id"])
        roster_ids = list(self.service.get_roster_student_ids(session_id))

        ctx = webrtc_streamer(
            key=f"passive-ai-monitor-{session_id}",
            rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
            video_processor_factory=lambda: PassiveAttendanceVideoProcessor(session_id=session_id, roster_ids=roster_ids),
            media_stream_constraints={"video": True, "audio": False},
            async_processing=False,
        )

        processor = getattr(ctx, "video_processor", None)
        if processor and getattr(processor, "latest_snapshot", None):
            st.session_state.passive_ai_snapshot = processor.latest_snapshot

    def _render_live_dashboard(self, active_session: Dict) -> None:
        session_id = int(active_session["id"])
        dashboard = self.service.get_live_dashboard(session_id)
        snapshot = st.session_state.get("passive_ai_snapshot", {})
        occupancy = dashboard.get("occupancy", {})
        latest_occ = occupancy.get("latest", {})

        recognized = int(snapshot.get("recognized_count", 0))
        unknown = int(snapshot.get("unknown_count", 0))
        detected = int(snapshot.get("detected_count", 0))

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Roster", dashboard.get("roster_total", 0))
            st.metric("Present", dashboard.get("present_count", 0))
            st.metric("Absent", dashboard.get("absent_count", 0))
        with col2:
            st.metric("Detected", detected)
            st.metric("Recognized", recognized)
            st.metric("Unknown", unknown)

        st.metric("Recognition Rate", f"{float(latest_occ.get('recognition_rate', 0.0)):.1f}%")

        history = occupancy.get("history", [])
        if history:
            st.markdown("#### Occupancy Analytics")
            hdf = pd.DataFrame(history)
            if "created_at" in hdf.columns:
                hdf["created_at"] = pd.to_datetime(hdf["created_at"], errors="coerce")
                hdf = hdf.sort_values("created_at")
                chart_df = hdf[["created_at", "detected_count", "recognized_count", "unknown_count"]].set_index("created_at")
            else:
                chart_df = hdf[["detected_count", "recognized_count", "unknown_count"]]
            st.line_chart(chart_df)

        st.markdown("#### Presence Logs")
        logs = dashboard.get("presence_logs", [])
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
        else:
            st.info("No presence logs yet.")

        st.markdown("#### Unknown / Event Alerts")
        events = dashboard.get("recent_events", [])
        if events:
            ev_df = pd.DataFrame(events)
            st.dataframe(ev_df, use_container_width=True, hide_index=True)
        else:
            st.info("No alert events yet.")
