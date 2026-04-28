"""
Alert history and management page
View and manage all system alerts
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from services.alert_service import AlertService, AlertSeverity, AlertType
from services.tracking_data_service import TrackingDataService
from ui.components.layout import render_page_header, card_container, section_title

logger = logging.getLogger(__name__)


class AlertHistoryPage:
    """Alert history and management page"""
    
    def __init__(self):
        self.alert_service = AlertService()
        self.tracking_service = TrackingDataService()
    
    def render(self):
        """Render alert history page"""
        render_page_header(
            title="🔔 Alert History & Management",
            subtitle="View, analyze, and manage all system alerts and notifications.",
            icon="📋",
        )
        
        # Navigation tabs
        tab1, tab2, tab3 = st.tabs(["📊 Overview", "📜 History", "👤 Student Alerts"])
        
        with tab1:
            self._render_overview_tab()
        
        with tab2:
            self._render_history_tab()
        
        with tab3:
            self._render_student_alerts_tab()
    
    def _render_overview_tab(self):
        """Render alert overview tab"""
        st.markdown("### Alert Statistics")
        
        # Get system summary
        summary = self.alert_service.get_system_alert_summary()
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🔴 Critical",
                summary.get('critical', 0),
                help="Critical severity alerts requiring immediate action"
            )
        
        with col2:
            st.metric(
                "⚠️ Total Active",
                summary.get('total_active', 0),
                help="All unresolved alerts"
            )
        
        with col3:
            st.metric(
                "👥 Affected",
                summary.get('students_affected', 0),
                help="Students with at least one active alert"
            )
        
        with col4:
            most_common = summary.get('most_common_type')
            st.metric(
                "📌 Most Common",
                most_common or "None",
                help="Most frequently occurring alert type"
            )
        
        st.markdown("---")
        
        # Alert type distribution
        st.markdown("### Alert Type Distribution")
        
        all_alerts = self.alert_service.get_alert_history(days_back=30, limit=1000)
        
        if all_alerts:
            alert_types = {}
            for alert in all_alerts:
                alert_type = alert['alert_type']
                alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
            
            # Create bar chart
            fig = go.Figure(data=[go.Bar(
                x=list(alert_types.keys()),
                y=list(alert_types.values()),
                marker=dict(color='#007bff'),
                text=list(alert_types.values()),
                textposition='auto',
            )])
            
            fig.update_layout(
                title="Alert Types (Last 30 Days)",
                xaxis_title="Alert Type",
                yaxis_title="Count",
                height=400,
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Severity distribution
        st.markdown("### Alert Severity Distribution")
        
        if all_alerts:
            severity_types = {}
            for alert in all_alerts:
                severity = alert['severity']
                severity_types[severity] = severity_types.get(severity, 0) + 1
            
            # Create pie chart
            colors_map = {
                'critical': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8'
            }
            
            fig = go.Figure(data=[go.Pie(
                labels=list(severity_types.keys()),
                values=list(severity_types.values()),
                marker=dict(colors=[colors_map.get(s, '#007bff') for s in severity_types.keys()]),
                textposition='inside',
                textinfo='label+percent'
            )])
            
            fig.update_layout(
                title="Alert Severity Distribution",
                height=400,
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def _render_history_tab(self):
        """Render alert history tab"""
        st.markdown("### Alert History")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            days_back = st.slider(
                "Time Period",
                min_value=1,
                max_value=90,
                value=7,
                step=1,
                help="Show alerts from the last N days"
            )
        
        with col2:
            severity_filter = st.multiselect(
                "Severity",
                options=["critical", "warning", "info"],
                default=["critical", "warning", "info"],
                help="Filter by alert severity"
            )
        
        with col3:
            status_filter = st.selectbox(
                "Status",
                options=["All", "Active", "Resolved"],
                help="Filter by alert status"
            )
        
        # Get alert history
        all_alerts = self.alert_service.get_alert_history(days_back=days_back, limit=500)
        
        # Apply filters
        filtered_alerts = [
            a for a in all_alerts
            if a['severity'] in severity_filter
        ]
        
        if status_filter == "Active":
            filtered_alerts = [a for a in filtered_alerts if not a['resolved_at']]
        elif status_filter == "Resolved":
            filtered_alerts = [a for a in filtered_alerts if a['resolved_at']]
        
        st.write(f"📊 Showing {len(filtered_alerts)} alerts")
        
        if not filtered_alerts:
            st.info("No alerts found matching the selected filters.")
            return
        
        # Display alerts in a table format
        for alert in filtered_alerts[:100]:  # Show top 100
            col1, col2, col3, col4 = st.columns([1, 3, 2, 1])
            
            # Severity badge
            severity_colors = {
                'critical': '🔴',
                'warning': '⚠️',
                'info': 'ℹ️'
            }
            
            with col1:
                st.write(severity_colors.get(alert['severity'], '•'))
            
            with col2:
                st.write(f"**{alert['title']}**")
                st.write(f"_{alert['message']}_")
                
                # Get student name if available
                try:
                    student = self.tracking_service.get_student_current_status(alert['student_id'])
                    student_name = student.get('name', f"Student {alert['student_id']}")
                    st.caption(f"👤 {student_name}")
                except:
                    st.caption(f"👤 Student {alert['student_id']}")
            
            with col3:
                created = datetime.fromisoformat(alert['created_at'])
                time_ago = self._time_ago(created)
                st.caption(f"🕐 {time_ago}")
                
                if alert['resolved_at']:
                    st.caption(f"✓ Resolved")
            
            with col4:
                if not alert['resolved_at']:
                    if st.button("Resolve", key=f"hist_resolve_{alert['id']}", use_container_width=True):
                        self.alert_service.resolve_alert(alert['id'])
                        st.success("Alert resolved!")
                        st.rerun()
            
            st.divider()
    
    def _render_student_alerts_tab(self):
        """Render per-student alerts tab"""
        st.markdown("### Student-Specific Alerts")
        
        # Select student
        students = self.tracking_service.get_all_students_status()
        
        if not students:
            st.info("No students found")
            return
        
        student_names = {s['student_id']: f"{s['name']} ({s['roll_number']})" for s in students}
        
        selected_student_id = st.selectbox(
            "Select Student",
            options=list(student_names.keys()),
            format_func=lambda x: student_names[x],
            help="Choose a student to view their alerts"
        )
        
        if selected_student_id:
            # Get student info
            student = self.tracking_service.get_student_current_status(selected_student_id)
            
            st.markdown(f"### 👤 {student.get('name', 'Student')}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Roll Number", student.get('roll_number', 'N/A'))
            
            with col2:
                st.metric("Status", student.get('status', 'unknown').title())
            
            with col3:
                st.metric("Time IN", student.get('time_in', 'N/A')[:8] if student.get('time_in') else 'N/A')
            
            with col4:
                st.metric("Time OUT", student.get('time_out', 'N/A')[:8] if student.get('time_out') else 'N/A')
            
            st.markdown("---")
            
            # Get alert statistics
            alert_stats = self.alert_service.get_student_alert_stats(selected_student_id, days_back=7)
            
            st.markdown("#### Alert Statistics (Last 7 Days)")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Alerts", alert_stats.get('total_alerts', 0))
            
            with col2:
                st.metric("Active", alert_stats.get('active_alerts', 0))
            
            with col3:
                st.metric("Critical", alert_stats.get('critical_count', 0))
            
            with col4:
                st.metric("Warnings", alert_stats.get('warning_count', 0))
            
            st.markdown("---")
            
            # Alert breakdown by type
            by_type = alert_stats.get('by_type', {})
            if by_type:
                st.markdown("#### Alerts by Type")
                
                type_df = pd.DataFrame([
                    {'Type': k, 'Count': v}
                    for k, v in by_type.items()
                ])
                
                st.bar_chart(type_df.set_index('Type'))
            
            st.markdown("---")
            
            # Alert history for this student
            st.markdown("#### Recent Alerts")
            
            days_back = st.slider(
                "Time Period",
                min_value=1,
                max_value=30,
                value=7,
                key="student_days_back"
            )
            
            student_alerts = self.alert_service.get_alert_history(
                student_id=selected_student_id,
                days_back=days_back,
                limit=50
            )
            
            if student_alerts:
                for alert in student_alerts:
                    severity_emoji = {
                        'critical': '🔴',
                        'warning': '⚠️',
                        'info': 'ℹ️'
                    }.get(alert['severity'], '•')
                    
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.write(f"{severity_emoji} **{alert['title']}**")
                        st.write(f"_{alert['message']}_")
                        created = datetime.fromisoformat(alert['created_at'])
                        st.caption(f"🕐 {self._time_ago(created)}")
                    
                    with col2:
                        if not alert['resolved_at']:
                            if st.button("Resolve", key=f"student_resolve_{alert['id']}", use_container_width=True):
                                self.alert_service.resolve_alert(alert['id'])
                                st.success("Alert resolved!")
                                st.rerun()
                    
                    st.divider()
            else:
                st.info("No alerts for this student in the selected period.")
            
            # Get attendance insights
            st.markdown("---")
            st.markdown("#### Attendance Insights")
            
            insights = self.tracking_service.get_student_attendance_insights(selected_student_id)
            
            if insights:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Attendance Rate", f"{insights.get('attendance_rate', 0):.1f}%")
                
                with col2:
                    st.metric("Late Arrivals", insights.get('late_arrivals', 0))
                
                with col3:
                    st.metric("Avg Duration", f"{insights.get('avg_duration_hours', 0):.1f}h")
                
                # Recommendations
                recommendations = insights.get('recommendations', [])
                if recommendations:
                    st.markdown("**Recommendations:**")
                    for rec in recommendations:
                        st.write(f"• {rec}")
    
    def _time_ago(self, dt: datetime) -> str:
        """Convert datetime to 'time ago' format"""
        now = datetime.now()
        diff = now - dt
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return f"{int(seconds)}s ago"
        elif seconds < 3600:
            return f"{int(seconds/60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h ago"
        elif seconds < 2592000:
            return f"{int(seconds/86400)}d ago"
        else:
            return dt.strftime("%Y-%m-%d")
