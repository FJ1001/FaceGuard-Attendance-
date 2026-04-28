"""
Analytics dashboard page - Completely redesigned
Provides meaningful insights and visualizations for attendance data
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

class AnalyticsPage:
    """Comprehensive analytics dashboard"""
    
    def __init__(self):
        self.analytics_service = AnalyticsService()
    
    def render(self):
        """Render comprehensive analytics dashboard"""
        st.markdown("## 📊 Advanced Analytics Dashboard")
        st.markdown("*Get insights into attendance patterns, student performance, and institutional trends*")
        
        # Date range selector
        self._render_date_selector()
        
        # Get analytics data
        days_back = st.session_state.get('analytics_days_back', 30)
        
        with st.spinner("📈 Generating comprehensive analytics..."):
            analytics_data = self.analytics_service.get_comprehensive_analytics(days_back)
        
        # Empty dict only on total failure; structured data with empty lists is still valid
        if not analytics_data:
            self._render_no_data_message()
            return
        
        # ── AI Insights card ──────────────────────────────────────────
        self._render_ai_insights(analytics_data)

        # Render analytics sections
        self._render_overview_section(analytics_data)
        self._render_attendance_trends(analytics_data)
        self._render_student_performance(analytics_data)
        self._render_course_analytics(analytics_data)
        self._render_time_patterns(analytics_data)
        self._render_alerts_section(analytics_data)
        
        # Export functionality
        self._render_export_section(analytics_data)
    
    def _render_ai_insights(self, analytics_data: Dict):
        """Render AI-generated narrative insights card."""
        insights = analytics_data.get("ai_insights", [])
        if not insights:
            return

        st.markdown("### 🤖 AI-Generated Insights")
        st.markdown(
            "<div style='background:linear-gradient(135deg,#1e3a5f 0%,#0f2640 100%);"
            "border-left:4px solid #3b82f6;border-radius:8px;padding:16px 20px;margin-bottom:16px;'>",
            unsafe_allow_html=True,
        )
        for insight in insights:
            st.markdown(f"- {insight}")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")

    def _render_date_selector(self):
        """Render date range selector"""
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            period_options = {
                "Last 7 Days": 7,
                "Last 30 Days": 30,
                "Last 60 Days": 60,
                "Last 90 Days": 90,
                "This Semester": 120
            }
            
            selected_period = st.selectbox(
                "📅 Analysis Period",
                options=list(period_options.keys()),
                index=1  # Default to 30 days
            )
            
            st.session_state.analytics_days_back = period_options[selected_period]
        
        with col2:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
        
        with col3:
            st.metric("📊 Period", selected_period)
    
    def _render_overview_section(self, analytics_data: Dict):
        """Render overview metrics section"""
        st.markdown("### 📈 Overview")
        
        overview = analytics_data.get('overview', {})
        weekly_summary = analytics_data.get('weekly_summary', {})
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "👥 Total Students",
                overview.get('total_students', 0)
            )
            
        with col2:
            present_today = overview.get('present_today', 0)
            absent_today = overview.get('absent_today', 0)
            st.metric(
                "✅ Present Today",
                present_today,
                delta=f"{absent_today} absent"
            )
        
        with col3:
            today_rate = overview.get('attendance_rate_today', 0)
            weekly_rate = overview.get('avg_weekly_rate', 0)
            delta_rate = today_rate - weekly_rate
            st.metric(
                "📊 Today's Rate",
                f"{today_rate}%",
                delta=f"{delta_rate:+.1f}% vs avg"
            )
        
        with col4:
            this_week = weekly_summary.get('this_week', 0)
            last_week = weekly_summary.get('last_week', 0)
            change = weekly_summary.get('change_percent', 0)
            st.metric(
                "📅 This Week",
                this_week,
                delta=f"{change:+.1f}% vs last week"
            )
        
        # Weekly trend indicator
        if weekly_summary:
            trend = weekly_summary.get('trend', 'stable')
            if trend == 'up':
                st.success("📈 Attendance trending upward this week!")
            elif trend == 'down':
                st.warning("📉 Attendance declining this week - monitor closely")
            else:
                st.info("➡️ Attendance stable this week")
    
    def _render_attendance_trends(self, analytics_data: Dict):
        """Render attendance trends visualization"""
        st.markdown("---")
        st.markdown("### 📈 Attendance Trends")
        
        daily_trends = analytics_data.get('daily_trends', [])
        
        if not daily_trends:
            st.info("📊 No trend data available for selected period")
            return
        
        # Create DataFrame for plotting
        trends_df = pd.DataFrame(daily_trends)
        trends_df['date'] = pd.to_datetime(trends_df['date'])
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=['Daily Attendance Count', 'Attendance Rate (%)'],
            vertical_spacing=0.1
        )
        
        # Attendance count line
        fig.add_trace(
            go.Scatter(
                x=trends_df['date'],
                y=trends_df['present_count'],
                mode='lines+markers',
                name='Present Count',
                line=dict(color='#10b981', width=3),
                marker=dict(size=6)
            ),
            row=1, col=1
        )
        
        # Attendance rate line
        fig.add_trace(
            go.Scatter(
                x=trends_df['date'],
                y=trends_df['attendance_rate'],
                mode='lines+markers',
                name='Attendance Rate',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=6),
                yaxis='y2'
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            height=500,
            showlegend=True,
            title_text="Attendance Trends Over Time"
        )
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Number of Students", row=1, col=1)
        fig.update_yaxes(title_text="Percentage (%)", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Insights
        col1, col2 = st.columns(2)
        
        with col1:
            avg_rate = trends_df['attendance_rate'].mean()
            max_rate = trends_df['attendance_rate'].max()
            min_rate = trends_df['attendance_rate'].min()
            
            st.info(f"📊 **Average Rate:** {avg_rate:.1f}%")
            st.success(f"📈 **Highest:** {max_rate:.1f}%")
            st.warning(f"📉 **Lowest:** {min_rate:.1f}%")
        
        with col2:
            # Best and worst days
            best_day = trends_df.loc[trends_df['attendance_rate'].idxmax()]
            worst_day = trends_df.loc[trends_df['attendance_rate'].idxmin()]
            
            st.success(f"🏆 **Best Day:** {best_day['day_name']} ({best_day['attendance_rate']:.1f}%)")
            st.error(f"📊 **Lowest Day:** {worst_day['day_name']} ({worst_day['attendance_rate']:.1f}%)")
    
    def _render_student_performance(self, analytics_data: Dict):
        """Render student performance analysis"""
        st.markdown("---")
        st.markdown("### 🎓 Student Performance Analysis")
        
        student_performance = analytics_data.get('student_performance', [])
        
        if not student_performance:
            st.info("📊 No student performance data available")
            return
        
        # Performance distribution
        performance_df = pd.DataFrame(student_performance)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Performance category distribution
            category_counts = performance_df['category'].value_counts()
            
            fig_pie = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                title="Student Performance Distribution",
                color_discrete_map={
                    'Excellent': '#10b981',
                    'Good': '#3b82f6',
                    'Average': '#f59e0b',
                    'Poor': '#ef4444'
                }
            )
            
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Top performers
            st.markdown("#### 🏆 Top Performers")
            top_performers = performance_df.nlargest(10, 'attendance_percentage')
            
            for idx, student in top_performers.iterrows():
                with st.container():
                    col_name, col_rate, col_status = st.columns([2, 1, 1])
                    
                    with col_name:
                        st.write(f"**{student['name']}**")
                        st.caption(f"{student['roll_number']} - {student['course']}")
                    
                    with col_rate:
                        st.metric("Rate", f"{student['attendance_percentage']:.1f}%")
                    
                    with col_status:
                        st.write(f"{student['status']} {student['category']}")
        
        # Detailed performance table
        st.markdown("#### 📋 Detailed Performance Report")
        
        # Add search functionality
        search_term = st.text_input("🔍 Search students", placeholder="Enter name or roll number")
        
        if search_term:
            filtered_df = performance_df[
                performance_df['name'].str.contains(search_term, case=False, na=False) |
                performance_df['roll_number'].str.contains(search_term, case=False, na=False)
            ]
        else:
            filtered_df = performance_df
        
        # Display table with styling
        st.dataframe(
            filtered_df[['name', 'roll_number', 'course', 'attendance_percentage', 'category', 'avg_arrival_time', 'late_days']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": "Student Name",
                "roll_number": "Roll Number",
                "course": "Course",
                "attendance_percentage": st.column_config.NumberColumn(
                    "Attendance %",
                    format="%.1f%%"
                ),
                "category": "Performance",
                "avg_arrival_time": "Avg Arrival",
                "late_days": "Late Days"
            }
        )
        
        # Performance insights
        st.markdown("#### 💡 Performance Insights")
        
        excellent_count = (performance_df['category'] == 'Excellent').sum()
        poor_count = (performance_df['category'] == 'Poor').sum()
        avg_attendance = performance_df['attendance_percentage'].mean()
        
        insight_col1, insight_col2, insight_col3 = st.columns(3)
        
        with insight_col1:
            st.metric("🌟 Excellent Performers", excellent_count)
        
        with insight_col2:
            st.metric("⚠️ Need Attention", poor_count)
        
        with insight_col3:
            st.metric("📊 Class Average", f"{avg_attendance:.1f}%")
    
    def _render_course_analytics(self, analytics_data: Dict):
        """Render course-wise analytics"""
        st.markdown("---")
        st.markdown("### 📚 Course-wise Analysis")
        
        course_analytics = analytics_data.get('course_analytics', [])
        
        if not course_analytics:
            st.info("📊 No course data available")
            return
        
        course_df = pd.DataFrame(course_analytics)
        
        # Course comparison chart
        fig = px.bar(
            course_df,
            x='course',
            y='attendance_rate',
            color='rating',
            title='Course-wise Attendance Rates',
            labels={'attendance_rate': 'Attendance Rate (%)', 'course': 'Course'},
            color_discrete_map={
                'Excellent': '#10b981',
                'Good': '#3b82f6',
                'Average': '#f59e0b',
                'Needs Attention': '#ef4444'
            }
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Course details table
        st.dataframe(
            course_df[['course', 'total_students', 'avg_daily_attendance', 'attendance_rate', 'rating']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "course": "Course",
                "total_students": "Total Students",
                "avg_daily_attendance": "Avg Daily Attendance",
                "attendance_rate": st.column_config.NumberColumn(
                    "Attendance Rate",
                    format="%.1f%%"
                ),
                "rating": "Performance Rating"
            }
        )
    
    def _render_time_patterns(self, analytics_data: Dict):
        """Render time pattern analysis"""
        st.markdown("---")
        st.markdown("### ⏰ Time Pattern Analysis")
        
        time_patterns = analytics_data.get('time_patterns', {})
        
        if not time_patterns:
            st.info("📊 No time pattern data available")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Hourly check-in patterns
            hourly_data = time_patterns.get('hourly_checkins', [])
            
            if hourly_data:
                hourly_df = pd.DataFrame(hourly_data)
                
                fig_hourly = px.bar(
                    hourly_df,
                    x='hour',
                    y='count',
                    title='Check-in Times Distribution',
                    labels={'count': 'Number of Check-ins', 'hour': 'Hour'}
                )
                
                fig_hourly.update_layout(height=400)
                st.plotly_chart(fig_hourly, use_container_width=True)
                
                peak_hour = time_patterns.get('peak_hour', 'N/A')
                st.info(f"🕐 **Peak Check-in Hour:** {peak_hour}")
        
        with col2:
            # Weekly patterns
            weekly_data = time_patterns.get('weekly_patterns', [])
            
            if weekly_data:
                weekly_df = pd.DataFrame(weekly_data)
                
                fig_weekly = px.bar(
                    weekly_df,
                    x='day',
                    y='count',
                    title='Day-wise Attendance Pattern',
                    labels={'count': 'Attendance Count', 'day': 'Day of Week'}
                )
                
                fig_weekly.update_layout(height=400)
                st.plotly_chart(fig_weekly, use_container_width=True)
                
                if weekly_df['count'].max() > 0:
                    best_day = weekly_df.loc[weekly_df['count'].idxmax(), 'day']
                    st.success(f"📅 **Best Attendance Day:** {best_day}")
    
    def _render_alerts_section(self, analytics_data: Dict):
        """Render alerts and warnings section"""
        st.markdown("---")
        st.markdown("### 🚨 Attendance Alerts")
        
        alerts = analytics_data.get('alerts', [])
        
        if not alerts:
            st.success("✅ No attendance alerts - All students are performing well!")
            return
        
        # Group alerts by severity
        high_alerts = [a for a in alerts if a.get('severity') == 'high']
        medium_alerts = [a for a in alerts if a.get('severity') == 'medium']
        
        if high_alerts:
            st.error(f"🚨 **{len(high_alerts)} High Priority Alerts**")
            
            for alert in high_alerts[:5]:  # Show top 5
                with st.container():
                    st.error(f"**{alert['title']}**")
                    st.write(f"📝 {alert['message']}")
                    st.write(f"💡 Action: {alert['action']}")
                    st.divider()
        
        if medium_alerts:
            st.warning(f"⚠️ **{len(medium_alerts)} Medium Priority Alerts**")
            
            with st.expander("View Medium Priority Alerts"):
                for alert in medium_alerts:
                    st.warning(f"**{alert['title']}:** {alert['message']}")
    
    def _render_export_section(self, analytics_data: Dict):
        """Render data export section"""
        st.markdown("---")
        st.markdown("### 📥 Export Analytics")

        try:
            from utils.pdf_report import build_analytics_pdf_summary

            pdf_bytes = build_analytics_pdf_summary(analytics_data)
            st.download_button(
                label="📄 Download PDF summary (archive)",
                data=pdf_bytes,
                file_name=f"analytics_summary_{date.today()}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="export_pdf_summary",
            )
        except Exception as e:
            logger.warning("PDF export unavailable: %s", e)
            st.caption("Install `fpdf2` for PDF export.")

        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export student performance
            if st.button("📊 Export Student Report", use_container_width=True):
                self._export_student_report(analytics_data)
        
        with col2:
            # Export course analytics
            if st.button("📚 Export Course Report", use_container_width=True):
                self._export_course_report(analytics_data)
        
        with col3:
            # Export comprehensive report
            if st.button("📈 Export Full Report", use_container_width=True):
                self._export_comprehensive_report(analytics_data)
    
    def _export_student_report(self, analytics_data: Dict):
        """Export student performance report"""
        student_performance = analytics_data.get('student_performance', [])
        
        if student_performance:
            df = pd.DataFrame(student_performance)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Student Report",
                data=csv,
                file_name=f"student_performance_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("No student data to export")
    
    def _export_course_report(self, analytics_data: Dict):
        """Export course analytics report"""
        course_analytics = analytics_data.get('course_analytics', [])
        
        if course_analytics:
            df = pd.DataFrame(course_analytics)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Course Report",
                data=csv,
                file_name=f"course_analytics_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("No course data to export")
    
    def _export_comprehensive_report(self, analytics_data: Dict):
        """Export comprehensive analytics report"""
        try:
            # Create comprehensive report
            report_data = {
                'Report Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Overview': analytics_data.get('overview', {}),
                'Weekly Summary': analytics_data.get('weekly_summary', {}),
                'Alerts Count': len(analytics_data.get('alerts', [])),
                'Student Performance': len(analytics_data.get('student_performance', [])),
                'Course Analytics': len(analytics_data.get('course_analytics', []))
            }
            
            # Convert to DataFrame for export
            report_df = pd.DataFrame([report_data])
            csv = report_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Comprehensive Report",
                data=csv,
                file_name=f"comprehensive_analytics_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"Error generating report: {e}")
    
    def _render_no_data_message(self):
        """Render message when no data is available"""
        st.info("📊 No analytics data available yet.")
        
        st.markdown("""
        ### 🚀 To generate meaningful analytics:
        
        1. **Register Students** - Add students to the system
        2. **Mark Attendance** - Record daily attendance for several days
        3. **Wait for Data** - Analytics improve with more data over time
        4. **Return Here** - Come back to view comprehensive insights
        """)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("👥 Add Students", use_container_width=True, key="analytics_add_students"):
                st.session_state.current_page = "Student Management"
                st.rerun()
        
        with col2:
            if st.button("📷 Mark Attendance", use_container_width=True, key="analytics_mark_attendance"):
                st.session_state.current_page = "Mark Attendance"
                st.rerun()
        
        with col3:
            if st.button("📊 Dashboard", use_container_width=True, key="analytics_dashboard"):
                st.session_state.current_page = "Dashboard Overview"
                st.rerun()
