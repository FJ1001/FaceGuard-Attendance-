"""
Live tracking and alerts dashboard page
Real-time monitoring of student status and alerts
"""
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from services.alert_service import AlertService, AlertSeverity
from services.tracking_data_service import TrackingDataService
from ui.components.layout import render_page_header, card_container, section_title

logger = logging.getLogger(__name__)


class LiveTrackingPage:
    """Live tracking and alerts dashboard"""
    
    def __init__(self):
        self.alert_service = AlertService()
        self.tracking_service = TrackingDataService()
    
    def render(self):
        """Render live tracking dashboard"""
        render_page_header(
            title="🎯 Live Tracking & Alerts",
            subtitle="Real-time student tracking, attendance status, and system alerts.",
            icon="📡",
        )
        
        # Auto-refresh setting
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown("### ⚡ Live Dashboard")
        with col2:
            refresh_interval = st.selectbox(
                "Refresh Interval",
                options=["Manual", "5s", "10s", "30s"],
                index=0,
                label_visibility="collapsed"
            )
        with col3:
            if st.button("🔄 Refresh Now", use_container_width=True):
                st.rerun()
        
        # Get current data
        class_overview = self.tracking_service.get_class_tracking_overview()
        active_alerts = self.alert_service.get_active_alerts()
        system_summary = self.alert_service.get_system_alert_summary()
        
        # Render sections
        self._render_system_status(class_overview, system_summary)
        self._render_tracking_report_section()
        self._render_active_alerts_section(active_alerts)
        self._render_real_time_student_status(class_overview)
        self._render_attendance_metrics(class_overview)
        self._render_pattern_analysis()
    
    def _render_system_status(self, class_overview: Dict, system_summary: Dict):
        """Render system status cards"""
        st.markdown("### 📊 System Status")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "👥 Total Students",
                class_overview.get('total_students', 0),
                help="Active students in system"
            )
        
        with col2:
            present = class_overview.get('present_today', 0)
            absent = class_overview.get('absent_today', 0)
            st.metric(
                "✅ Present",
                present,
                delta=f"{absent} absent"
            )
        
        with col3:
            rate = class_overview.get('attendance_rate', 0)
            st.metric(
                "📈 Attendance Rate",
                f"{rate}%",
                help="Today's attendance rate"
            )
        
        with col4:
            critical = system_summary.get('critical', 0)
            total_active = system_summary.get('total_active', 0)
            st.metric(
                "🚨 Alerts",
                total_active,
                delta=f"{critical} critical" if critical > 0 else "All good"
            )
        
        with col5:
            affected = system_summary.get('students_affected', 0)
            st.metric(
                "⚠️ Affected",
                affected,
                help="Students with active alerts"
            )
        
        st.markdown("---")

    def _render_tracking_report_section(self):
        """Render a short report generated from live tracking data."""
        st.markdown("### 🧾 Quick Tracking Report")

        report_days = st.selectbox(
            "Report period",
            options=[3, 7, 14],
            index=1,
            help="Choose how many days of tracking to include in the report",
            key="live_tracking_report_days",
        )

        report = self.tracking_service.generate_live_tracking_report(days_back=report_days)

        if not report:
            st.info("No report data available yet.")
            return

        summary = report.get('summary', {})
        insights = report.get('insights', [])
        top_alerts = report.get('top_alerts', [])
        top_students = report.get('top_students', [])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Attendance", f"{summary.get('attendance_rate', 0):.1f}%")
        with col2:
            st.metric("Present", summary.get('present_today', 0))
        with col3:
            st.metric("Active Alerts", summary.get('active_alerts', 0))
        with col4:
            st.metric("Critical", summary.get('critical_alerts', 0))

        if insights:
            st.markdown("#### Key Insights")
            for insight in insights:
                st.write(f"• {insight}")

        if top_alerts:
            st.markdown("#### Top Alerts")
            for alert in top_alerts[:3]:
                st.write(f"• {alert.get('title', 'Alert')} - {alert.get('message', '')}")

        if top_students:
            st.markdown("#### Top Tracked Students")
            report_df = pd.DataFrame(top_students)
            st.dataframe(report_df, use_container_width=True, hide_index=True)

        export_col1, export_col2, export_col3 = st.columns(3)

        csv_bytes = self._build_tracking_report_csv(report)
        pdf_bytes = self._build_tracking_report_pdf(report)
        json_payload = json.dumps(report, indent=2, default=str)

        with export_col1:
            st.download_button(
                "📄 Download CSV",
                data=csv_bytes,
                file_name=f"live_tracking_report_{report_days}d.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with export_col2:
            st.download_button(
                "📕 Download PDF",
                data=pdf_bytes,
                file_name=f"live_tracking_report_{report_days}d.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        with export_col3:
            st.download_button(
                "⬇️ Download JSON",
                data=json_payload,
                file_name=f"live_tracking_report_{report_days}d.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown("---")

    def _build_tracking_report_csv(self, report: Dict) -> str:
        """Build a compact CSV export from the report summary."""
        summary = report.get('summary', {})
        counts = report.get('status_counts', {})

        rows = [
            {"section": "summary", "key": "generated_at", "value": report.get('generated_at', '')},
            {"section": "summary", "key": "period_days", "value": report.get('period_days', '')},
            {"section": "summary", "key": "total_students", "value": summary.get('total_students', 0)},
            {"section": "summary", "key": "present_today", "value": summary.get('present_today', 0)},
            {"section": "summary", "key": "absent_today", "value": summary.get('absent_today', 0)},
            {"section": "summary", "key": "attendance_rate", "value": summary.get('attendance_rate', 0)},
            {"section": "summary", "key": "active_alerts", "value": summary.get('active_alerts', 0)},
            {"section": "summary", "key": "critical_alerts", "value": summary.get('critical_alerts', 0)},
            {"section": "status", "key": "present", "value": counts.get('present', 0)},
            {"section": "status", "key": "completed", "value": counts.get('completed', 0)},
            {"section": "status", "key": "absent", "value": counts.get('absent', 0)},
        ]

        for insight in report.get('insights', [])[:3]:
            rows.append({"section": "insight", "key": "note", "value": insight})

        for alert in report.get('top_alerts', [])[:5]:
            rows.append({
                "section": "alert",
                "key": alert.get('title', 'Alert'),
                "value": alert.get('message', ''),
            })

        df = pd.DataFrame(rows)
        return df.to_csv(index=False)

    def _build_tracking_report_pdf(self, report: Dict) -> bytes:
        """Build a short PDF export from the live tracking report."""
        from utils.pdf_report import build_live_tracking_pdf_summary

        return build_live_tracking_pdf_summary(report)
    
    def _render_active_alerts_section(self, alerts: List[Dict]):
        """Render active alerts section"""
        st.markdown("### 🚨 Active Alerts")
        
        if not alerts:
            st.success("✅ No active alerts. Everything is normal!")
            return
        
        # Separate alerts by severity
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        warning_alerts = [a for a in alerts if a['severity'] == 'warning']
        info_alerts = [a for a in alerts if a['severity'] == 'info']
        
        # Display critical alerts
        if critical_alerts:
            with st.container(border=True):
                st.markdown("#### 🔴 Critical Alerts")
                for alert in critical_alerts[:5]:  # Show top 5
                    col1, col2, col3 = st.columns([3, 4, 1])
                    
                    with col1:
                        # Get student name
                        student = self.tracking_service.get_student_current_status(alert['student_id'])
                        student_name = student.get('name', f"Student {alert['student_id']}")
                        st.write(f"👤 **{student_name}**")
                    
                    with col2:
                        st.write(f"**{alert['title']}**")
                        st.write(f"_{alert['message']}_")
                        st.caption(f"🕐 {alert['created_at']}")
                    
                    with col3:
                        if st.button("✓ Resolve", key=f"resolve_{alert['id']}"):
                            self.alert_service.resolve_alert(alert['id'])
                            st.success("Alert resolved!")
                            st.rerun()
                    
                    st.divider()
        
        # Display warning alerts
        if warning_alerts:
            with st.expander(f"⚠️ Warning Alerts ({len(warning_alerts)})", expanded=False):
                for alert in warning_alerts[:10]:
                    student = self.tracking_service.get_student_current_status(alert['student_id'])
                    student_name = student.get('name', f"Student {alert['student_id']}")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"👤 **{student_name}** - {alert['title']}")
                        st.write(f"_{alert['message']}_")
                    with col2:
                        if st.button("✓", key=f"warn_resolve_{alert['id']}", use_container_width=True):
                            self.alert_service.resolve_alert(alert['id'])
                            st.rerun()
        
        # Display info alerts
        if info_alerts:
            with st.expander(f"ℹ️ Info Alerts ({len(info_alerts)})", expanded=False):
                for alert in info_alerts[:10]:
                    st.info(f"{alert['title']} - {alert['message']}")
    
    def _render_real_time_student_status(self, class_overview: Dict):
        """Render real-time student status table"""
        st.markdown("### 👥 Real-Time Student Status")
        
        students_status = self.tracking_service.get_all_students_status()
        
        if not students_status:
            st.info("No student data available")
            return
        
        # Create DataFrame for better display
        df_data = []
        for student in students_status:
            status_icon = "🟢" if student['status'] == 'present' else \
                         "🔴" if student['status'] == 'absent' else "🟡"
            
            time_in = student['time_in']
            if time_in:
                time_in = datetime.fromisoformat(time_in).strftime("%H:%M:%S")
            
            time_out = student['time_out']
            if time_out:
                time_out = datetime.fromisoformat(time_out).strftime("%H:%M:%S")
            
            df_data.append({
                'Status': status_icon,
                'Name': student['name'],
                'Roll': student['roll_number'],
                'Time IN': time_in or '-',
                'Time OUT': time_out or '-',
            })
        
        df = pd.DataFrame(df_data)
        
        # Display with styling
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )
        
        with col2:
            # Filter options
            filter_status = st.selectbox(
                "Filter by Status",
                options=["All", "Present", "Absent", "Completed"],
                key="status_filter"
            )
            
            if filter_status != "All":
                filter_map = {
                    "Present": "present",
                    "Absent": "absent",
                    "Completed": "completed"
                }
                filtered = [s for s in students_status if s['status'] == filter_map[filter_status]]
                st.metric(f"{filter_status}", len(filtered))
    
    def _render_attendance_metrics(self, class_overview: Dict):
        """Render attendance metrics visualization"""
        st.markdown("### 📊 Attendance Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart for today's attendance
            labels = ["Present", "Absent"]
            values = [
                class_overview.get('present_today', 0),
                class_overview.get('absent_today', 0)
            ]
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=['#28a745', '#dc3545']),
                textposition='inside',
                textinfo='label+percent'
            )])
            
            fig.update_layout(
                title="Today's Attendance",
                height=350,
                showlegend=True,
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Status breakdown
            st.markdown("#### Status Breakdown")
            
            present = class_overview.get('present_today', 0)
            departed = class_overview.get('departed', 0)
            still_present = class_overview.get('still_present', 0)
            absent = class_overview.get('absent_today', 0)
            
            st.metric("✅ Arrived", present)
            st.metric("🚪 Departed", departed)
            st.metric("🟢 Still Present", still_present)
            st.metric("❌ Absent", absent)
        
        st.markdown("---")
    
    def _render_pattern_analysis(self):
        """Render attendance pattern analysis"""
        st.markdown("### 📈 Attendance Patterns (Last 7 Days)")
        
        pattern_data = self.tracking_service.get_attendance_pattern_analysis(days_back=7)
        
        if pattern_data.get('daily_stats'):
            daily_stats = pattern_data['daily_stats']
            
            # Create bar chart
            dates = [d['date'] for d in daily_stats]
            present_counts = [d['present'] for d in daily_stats]
            
            fig = go.Figure(data=[go.Bar(
                x=dates,
                y=present_counts,
                marker=dict(color='#007bff'),
                text=present_counts,
                textposition='auto',
            )])
            
            fig.update_layout(
                title="Daily Attendance Trend",
                xaxis_title="Date",
                yaxis_title="Students Present",
                height=350,
                hovermode='x unified',
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Most absent students
            if pattern_data.get('most_absent_students'):
                st.markdown("#### Most Absent Students (Last 7 Days)")
                
                absent_df = pd.DataFrame(pattern_data['most_absent_students'])
                st.dataframe(absent_df, use_container_width=True, hide_index=True)
    
    def _render_recent_activity(self, class_overview: Dict):
        """Render recent activity section"""
        st.markdown("### 🕐 Recent Activity")
        
        recent = class_overview.get('recent_activity', [])
        
        if not recent:
            st.info("No recent activity")
            return
        
        for activity in recent:
            if activity['time']:
                time_str = datetime.fromisoformat(activity['time']).strftime("%H:%M:%S")
                st.write(f"👤 {activity['name']} - {time_str}")
