"""Live focus and energy monitoring page."""

from __future__ import annotations

import logging
import json
from datetime import datetime

import cv2
import numpy as np
import streamlit as st

from config.settings import FOCUS_MONITORING_ENABLED
from face_focus.focus_energy_service import FocusEnergyService
from services.focus_session_service import FocusSessionService
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


class FocusEnergyPage:
    """Displays live focus scoring and instant alerts."""

    def __init__(self) -> None:
        self.focus_service = FocusEnergyService()
        self.focus_session_service = FocusSessionService()

    def render(self) -> None:
        render_page_header(
            title="Focus & Energy Monitor",
            subtitle="AI-assisted webcam checks that highlight low focus, motion blur, and poor lighting.",
            icon="🧠",
        )

        render_info_strip(
            items=[
                ("Live score", "Tracks a simple 0-100 focus energy signal from the webcam frame."),
                ("Alerts", "Warns when the face is off-center, blurry, dark, or too small."),
                ("Privacy", "Frame analysis stays local to the Streamlit session."),
            ]
        )

        self._render_student_selector()

        if not FOCUS_MONITORING_ENABLED:
            st.warning("Focus monitoring is disabled in configuration.")
            return

        col_live, col_snapshot = st.columns([3, 2])

        with col_live:
            with card_container():
                section_title("Live Monitor", icon="🎥")
                self._render_live_monitor()

        with col_snapshot:
            with card_container():
                section_title("Snapshot Check", icon="📸")
                self._render_snapshot_check()

        with st.expander("How the score works", expanded=False):
            st.markdown(
                """
                - **Face presence**: no face means a critical alert.
                - **Eyes visible**: open, visible eyes increase the score.
                - **Centering**: the face should stay near the middle of the frame.
                - **Lighting and blur**: dark or blurry frames lower the score.
                """
            )

    def _render_live_monitor(self) -> None:
        if webrtc_streamer is None:
            st.error("streamlit-webrtc is not installed.")
            st.code("pip install streamlit-webrtc av", language="bash")
            if _IMPORT_ERROR:
                st.caption(_IMPORT_ERROR)
            return

        from face_focus.webrtc_processor import FocusEnergyVideoProcessor

        st.caption("Start the camera and watch the score overlay update on the video feed.")

        ctx = webrtc_streamer(
            key="focus-energy-webrtc",
            rtc_configuration=RTCConfiguration(
                {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            ),
            video_processor_factory=FocusEnergyVideoProcessor,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=False,
        )

        session_state = getattr(ctx, "state", None)
        st.session_state.focus_energy_webrtc_active = bool(
            getattr(session_state, "playing", False) if session_state is not None else False
        )

        processor = getattr(ctx, "video_processor", None)
        if processor and getattr(processor, "latest_analysis", None):
            self._capture_live_session_analysis(processor.latest_analysis)
            self._render_live_stats(processor.latest_analysis)
            self._render_focus_report_actions(processor.latest_analysis, report_label="live")

        self._render_session_report_section()

    def _render_live_stats(self, analysis: dict) -> None:
        score = float(analysis.get("focus_score", 0.0))
        rolling_score = float(analysis.get("rolling_focus_score", score))
        status = analysis.get("rolling_status", analysis.get("status", "critical"))
        sample_count = int(analysis.get("sample_count", 0))

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Live Score", f"{score:.1f}")
        with col2:
            st.metric("Rolling Avg", f"{rolling_score:.1f}")
        with col3:
            st.metric("Live Status", status.title())

        if status == "focused":
            st.success(f"Average focus is strong across the last {sample_count} frames.")
        elif status == "attention":
            st.warning(f"Average focus is drifting. Review the last {sample_count} frames.")
        else:
            st.error(f"Average focus is low across the last {sample_count} frames.")

        for alert in analysis.get("rolling_alerts", []):
            st.caption(f"• {alert}")

        st.caption(
            f"Rolling average uses the last {analysis.get('average_window', 0)} frames and updates inside the live video overlay."
        )

    def _render_snapshot_check(self) -> None:
        camera_input = st.camera_input("Take a focus snapshot")
        uploaded_file = st.file_uploader(
            "Or upload an image", type=["png", "jpg", "jpeg"], key="focus_energy_upload"
        )

        image = None
        if camera_input is not None:
            image = self._convert_image_input(camera_input)
        elif uploaded_file is not None:
            image = self._convert_image_input(uploaded_file)

        if image is None:
            st.info("Capture a photo to get a focus energy score and alert summary.")
            return

        analysis = self.focus_service.analyze_image(image)
        self._render_analysis(analysis)

    def _render_analysis(self, analysis: dict) -> None:
        score = float(analysis.get("focus_score", 0))
        status = analysis.get("status", "critical")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Focus Score", f"{score:.1f}")
        with col2:
            st.metric("Status", status.title())

        if status == "focused":
            st.success("Focus looks strong right now.")
        elif status == "attention":
            st.warning("Focus is dropping. Ask the user to adjust posture or lighting.")
        else:
            st.error("Low focus detected. The current frame needs attention.")

        for alert in analysis.get("alerts", []):
            st.caption(f"• {alert}")

        components = analysis.get("components", {})
        if components:
            st.markdown("#### Component Breakdown")
            metric_cols = st.columns(3)
            with metric_cols[0]:
                st.metric("Eyes", f"{components.get('eyes', 0):.1f}")
                st.metric("Centering", f"{components.get('centering', 0):.1f}")
            with metric_cols[1]:
                st.metric("Clarity", f"{components.get('clarity', 0):.1f}")
                st.metric("Brightness", f"{components.get('brightness', 0):.1f}")
            with metric_cols[2]:
                st.metric("Face Size", f"{components.get('face_size', 0):.1f}")
                st.metric("Face %", f"{analysis.get('face_ratio', 0):.1f}%")

        self._render_focus_report_actions(analysis, report_label="snapshot")

    def _render_focus_report_actions(self, analysis: dict, report_label: str) -> None:
        """Render simple export buttons for focus analysis."""
        from utils.pdf_report import build_focus_analysis_pdf_summary

        pdf_bytes = build_focus_analysis_pdf_summary(analysis)

        report_col1, report_col2 = st.columns(2)
        with report_col1:
            st.download_button(
                label="📄 Download Focus PDF",
                data=pdf_bytes,
                file_name=f"focus_{report_label}_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"focus_pdf_{report_label}",
            )
        with report_col2:
            st.download_button(
                label="⬇️ Download Analysis JSON",
                data=json.dumps(analysis, indent=2, default=str),
                file_name=f"focus_{report_label}_analysis.json",
                mime="application/json",
                use_container_width=True,
                key=f"focus_json_{report_label}",
            )

    def _capture_live_session_analysis(self, analysis: dict) -> None:
        """Store a compact live-session history so a final PDF can be generated after stop."""
        history = st.session_state.setdefault("focus_live_history", [])
        snapshot = {
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "focus_score": float(analysis.get("focus_score", 0.0)),
            "rolling_focus_score": float(analysis.get("rolling_focus_score", analysis.get("focus_score", 0.0))),
            "rolling_status": analysis.get("rolling_status", analysis.get("status", "critical")),
            "sample_count": int(analysis.get("sample_count", 0)),
            "alerts": list(analysis.get("rolling_alerts", analysis.get("alerts", []))),
            "components": analysis.get("components", {}),
        }

        history.append(snapshot)
        st.session_state.focus_live_history = history[-50:]
        st.session_state.focus_last_live_analysis = snapshot

    def _render_session_report_section(self) -> None:
        """Render the final report once the live stream is stopped or paused."""
        history = st.session_state.get("focus_live_history", [])
        if not history:
            return

        last_analysis = st.session_state.get("focus_last_live_analysis", history[-1])
        st.markdown("#### Final Live Session Report")

        is_active = False
        try:
            is_active = bool(st.session_state.get("focus_energy_webrtc_active", False))
        except Exception:
            is_active = False

        if is_active:
            st.caption("Keep the camera running to collect more frames. The final report becomes available after you stop the video.")
            return

        from utils.pdf_report import build_focus_analysis_pdf_summary

        avg_focus = round(sum(item.get("focus_score", 0.0) for item in history) / max(len(history), 1), 1)
        avg_rolling = round(sum(item.get("rolling_focus_score", 0.0) for item in history) / max(len(history), 1), 1)
        min_focus = round(min(item.get("focus_score", 0.0) for item in history), 1)
        max_focus = round(max(item.get("focus_score", 0.0) for item in history), 1)
        alerts_count = int(sum(len(item.get("alerts", [])) for item in history))

        final_report = {
            "focus_score": last_analysis.get("focus_score", 0.0),
            "rolling_focus_score": avg_rolling,
            "rolling_status": last_analysis.get("rolling_status", last_analysis.get("status", "critical")),
            "sample_count": len(history),
            "rolling_alerts": last_analysis.get("alerts", []),
            "components": last_analysis.get("components", {}),
            "avg_focus_score": avg_focus,
            "avg_rolling_score": avg_rolling,
            "min_focus_score": min_focus,
            "max_focus_score": max_focus,
            "alerts_count": alerts_count,
            "final_status": last_analysis.get("rolling_status", "critical"),
        }

        st.success(f"Session captured {len(history)} frame snapshots. The PDF below summarizes the stopped video session.")
        summary_cols = st.columns(5)
        with summary_cols[0]:
            st.metric("Avg Focus", f"{avg_focus:.1f}")
        with summary_cols[1]:
            st.metric("Avg Rolling", f"{avg_rolling:.1f}")
        with summary_cols[2]:
            st.metric("Min", f"{min_focus:.1f}")
        with summary_cols[3]:
            st.metric("Max", f"{max_focus:.1f}")
        with summary_cols[4]:
            st.metric("Alerts", alerts_count)

        st.download_button(
            label="📄 Download Final Session PDF",
            data=build_focus_analysis_pdf_summary(final_report),
            file_name="focus_final_session_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="focus_final_session_pdf",
        )

        st.download_button(
            label="⬇️ Download Final Session JSON",
            data=json.dumps({"frames": history, "summary": final_report}, indent=2, default=str),
            file_name="focus_final_session_report.json",
            mime="application/json",
            use_container_width=True,
            key="focus_final_session_json",
        )

        selected_student_id = st.session_state.get("focus_selected_student_id")
        selected_student_label = st.session_state.get("focus_selected_student_label", "")
        if selected_student_id:
            session_signature = (
                f"{selected_student_id}|{history[0].get('captured_at','')}|"
                f"{history[-1].get('captured_at','')}|{len(history)}"
            )
            already_saved = st.session_state.get("focus_saved_session_signature") == session_signature
            if already_saved:
                st.caption(f"Saved to student analytics: {selected_student_label}")
            else:
                if st.button("💾 Save Session to Student Analytics", use_container_width=True, key="focus_save_session"):
                    success = self.focus_session_service.save_session_report(
                        student_id=int(selected_student_id),
                        summary=final_report,
                        frames=history,
                    )
                    if success:
                        st.session_state.focus_saved_session_signature = session_signature
                        st.success(f"Saved session analytics for {selected_student_label}.")
                    else:
                        st.error("Could not save this session analytics.")
        else:
            st.info("Select a student above to save this final session into admin analytics.")

    def _render_student_selector(self) -> None:
        """Pick the student to associate with the current live focus session."""
        try:
            from services.student_service import StudentService

            students = StudentService().get_all_students()
        except Exception as exc:
            logger.warning("Could not load students for focus selector: %s", exc)
            students = []

        if not students:
            st.info("No students available. Register students first to save focus session analytics.")
            st.session_state.focus_selected_student_id = None
            st.session_state.focus_selected_student_label = ""
            return

        options = [
            (student.get("id"), f"{student.get('name', 'Unknown')} ({student.get('roll_number', 'N/A')})")
            for student in students
        ]
        selected = st.selectbox(
            "Student for this live session",
            options=options,
            format_func=lambda item: item[1],
            key="focus_student_selector",
        )

        st.session_state.focus_selected_student_id = selected[0]
        st.session_state.focus_selected_student_label = selected[1]

    def _convert_image_input(self, image_input) -> np.ndarray | None:
        try:
            if hasattr(image_input, "read"):
                file_bytes = image_input.read()
            elif hasattr(image_input, "getvalue"):
                file_bytes = image_input.getvalue()
            else:
                return None

            nparr = np.frombuffer(file_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return None
            return image
        except Exception as exc:
            logger.error("Failed to convert focus image input: %s", exc)
            return None