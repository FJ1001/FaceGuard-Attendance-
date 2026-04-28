"""
Main dashboard page component - Complete version
Extracted from app.py dashboard functionality
"""
import streamlit as st
import pandas as pd
import logging
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from auth.session_manager import SessionManager
from services.attendance_service import AttendanceService
from services.student_service import StudentService
from ui.pages.student_management import StudentManagementPage
from ui.pages.attendance_page import AttendancePage
from ui.pages.analytics_page import AnalyticsPage
from ui.components.layout import render_page_header, render_kpi_row, section_title
from ui.theme import PremiumTheme

logger = logging.getLogger(__name__)

class DashboardPage:
    """Main dashboard page component with complete error handling"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        try:
            self.attendance_service = AttendanceService()
            self.student_service = StudentService()
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            self.attendance_service = None
            self.student_service = None
    
    def render(self):
        """Render appropriate dashboard based on user role"""
        current_user = self.session_manager.get_current_user()
        
        if not current_user:
            st.error("❌ Authentication error. Please login again.")
            self.session_manager.logout_user()
            st.rerun()
            return
        
        # Check session timeout
        if self.session_manager.check_session_timeout():
            st.warning("🕐 Session expired. Please login again.")
            st.rerun()
            return
        
        # Refresh session
        self.session_manager.refresh_session()
        
        # Render dashboard based on role
        if current_user['role'] == 'admin':
            self._render_admin_dashboard(current_user)
        else:
            self._render_user_dashboard(current_user)
    
    def _render_admin_dashboard(self, user: Dict):
        """Render admin dashboard"""
        render_page_header(
            title="Admin Dashboard",
            subtitle="Realtime overview of students, attendance and system activity.",
            icon="📊",
        )
        
        # Sidebar navigation
        self._render_admin_sidebar(user)
        
        # Show current page based on session state
        current_page = st.session_state.get('current_page', 'Mark Attendance')
        
        if current_page == "Dashboard Overview":
            self._render_dashboard_overview()
        elif current_page == "Student Management":
            student_page = StudentManagementPage()
            student_page.render()
        elif current_page == "Mark Attendance":
            attendance_page = AttendancePage()
            attendance_page.render()
        elif current_page == "Live Mask Detection":
            from ui.pages.live_mask_page import LiveMaskPage

            LiveMaskPage().render()
        elif current_page == "Attendance Records":
            self._render_attendance_records()
        elif current_page == "Analytics":
            # Use the enhanced analytics page
            try:
                analytics_page = AnalyticsPage()
                analytics_page.render()
            except Exception as e:
                logger.error(f"Analytics error: {e}")
                st.error(f"❌ Analytics error: {str(e)}")
                st.info("💡 Try refreshing the page or check if students are registered")
        elif current_page == "Focus Energy Monitor":
            from ui.pages.focus_energy_page import FocusEnergyPage

            FocusEnergyPage().render()
        elif current_page == "Live Tracking & Alerts":
            from ui.pages.live_tracking_page import LiveTrackingPage

            LiveTrackingPage().render()
        elif current_page == "Alert History":
            from ui.pages.alert_history_page import AlertHistoryPage

            AlertHistoryPage().render()
        elif current_page == "Passive AI Attendance":
            from ui.pages.passive_ai_attendance_page import PassiveAIAttendancePage

            PassiveAIAttendancePage().render()
        elif current_page == "System Health":
            from ui.pages.health_page import HealthPage

            HealthPage().render()
        elif current_page == "User Management":
            self._render_user_management()
        elif current_page == "Danger Zone":
            self._render_danger_zone()
    
    def _render_user_dashboard(self, user: Dict):
        """Render user/student dashboard"""
        current_page = st.session_state.get('current_page', 'Mark Attendance')

        page_headers = {
            "User Dashboard": (
                "Student Dashboard",
                "Quick overview of your institution's attendance status.",
                "🎓",
            ),
            "Mark Attendance": (
                "Live Face Attendance",
                "Use the camera or upload a photo to mark IN/OUT attendance in real time.",
                "📷",
            ),
            "Live Mask Detection": (
                "Live Mask Detection",
                "Real-time webcam preview for mask and face-covering checks.",
                "🎥",
            ),
            "Focus Energy Monitor": (
                "Focus & Energy Monitor",
                "AI-assisted webcam checks that highlight low focus, motion blur, and poor lighting.",
                "🧠",
            ),
        }
        title, subtitle, icon = page_headers.get(
            current_page,
            (
                "Student Dashboard",
                "Quick overview of your institution's attendance status.",
                "🎓",
            ),
        )

        render_page_header(title=title, subtitle=subtitle, icon=icon)

        # Sidebar navigation
        self._render_user_sidebar(user)
        
        if current_page == "User Dashboard":
            self._render_user_dashboard_content()
        elif current_page == "Mark Attendance":
            attendance_page = AttendancePage()
            attendance_page.render()
        elif current_page == "Live Mask Detection":
            from ui.pages.live_mask_page import LiveMaskPage

            LiveMaskPage().render()
        elif current_page == "Focus Energy Monitor":
            from ui.pages.focus_energy_page import FocusEnergyPage

            FocusEnergyPage().render()
    
    def _render_admin_sidebar(self, user: Dict):
        """Render admin sidebar navigation"""
        with st.sidebar:
            st.markdown("### 🎯 Attendance Console")
            
            primary_buttons = [
                ("📷 Mark Attendance", "Mark Attendance", "admin_nav_attendance"),
                ("👥 Student Management", "Student Management", "admin_nav_students"),
                ("📝 Attendance Records", "Attendance Records", "admin_nav_records"),
            ]
            insight_buttons = [
                ("📈 Dashboard Overview", "Dashboard Overview", "admin_nav_dashboard"),
                ("📊 Analytics", "Analytics", "admin_nav_analytics"),
                ("🎯 Live Tracking & Alerts", "Live Tracking & Alerts", "admin_nav_tracking"),
                ("🔔 Alert History", "Alert History", "admin_nav_alert_history"),
                ("📡 Passive AI Attendance", "Passive AI Attendance", "admin_nav_passive_ai"),
            ]
            admin_buttons = [
                ("🩺 System Health", "System Health", "admin_nav_health"),
                ("🎥 Live Mask Detection", "Live Mask Detection", "admin_nav_mask"),
                ("🧠 Focus & Energy Monitor", "Focus Energy Monitor", "admin_nav_focus"),
                ("👤 User Management", "User Management", "admin_nav_users"),
                ("⚠️ Danger Zone", "Danger Zone", "admin_nav_danger"),
            ]
            
            st.caption("Daily operation")
            self._render_sidebar_buttons(primary_buttons)

            st.caption("Review and insights")
            self._render_sidebar_buttons(insight_buttons)

            st.caption("Administration")
            self._render_sidebar_buttons(admin_buttons)
            
            st.markdown("---")
            # Demo mode — load sample data for judging / presentations
            st.caption("Demo")
            if st.button("🎬 Load Demo Data", use_container_width=True, key="admin_nav_demo"):
                with st.spinner("Loading demo students and attendance records…"):
                    try:
                        import sys, os
                        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from scripts.seed_demo import seed_demo_data
                        ok, msg = seed_demo_data()
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")
                    except Exception as _e:
                        st.error(f"❌ Demo load failed: {_e}")

            st.markdown("---")
            self._render_user_info_sidebar(user)
    
    def _render_user_sidebar(self, user: Dict):
        """Render user sidebar navigation"""
        with st.sidebar:
            st.markdown("### 🎯 Attendance Console")
            
            nav_buttons = [
                ("📷 Mark Attendance", "Mark Attendance", "user_nav_attendance"),
                ("📈 My Dashboard", "User Dashboard", "user_nav_dashboard"),
                ("🎥 Live Mask Detection", "Live Mask Detection", "user_nav_mask"),
                ("🧠 Focus & Energy Monitor", "Focus Energy Monitor", "user_nav_focus"),
            ]
            
            self._render_sidebar_buttons(nav_buttons)
            
            st.markdown("---")
            self._render_user_info_sidebar(user)

    def _render_sidebar_buttons(self, buttons: List[Tuple[str, str, str]]) -> None:
        """Render sidebar navigation buttons with the current page disabled."""
        current_page = st.session_state.get("current_page", "Mark Attendance")
        for button_text, page_name, key in buttons:
            is_current = current_page == page_name
            label = f"▶ {button_text}" if is_current else button_text
            if st.button(label, use_container_width=True, key=key, disabled=is_current):
                st.session_state.current_page = page_name
                st.rerun()
    
    def _render_user_info_sidebar(self, user: Dict):
        """Render user info and logout button"""
        st.markdown(f"**Logged in as:** {user['email']}")
        st.markdown(f"**Role:** {user['role'].title()}")
        
        if user.get('login_time'):
            st.markdown(f"**Login time:** {user['login_time'].strftime('%H:%M')}")
        
        # Add theme toggle
        st.markdown("---")
        st.markdown("### 🎨 Theme")
        try:
            from ui.components.theme_toggle import theme_toggle
            theme_toggle.render_toggle_button()
        except ImportError:
            pass  # Theme toggle not available
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, type="secondary", key="logout_btn"):
            self.session_manager.logout_user()
            st.rerun()
        
        # Version footer
        st.markdown("---")
        st.markdown(
            "<div style='text-align:center;color:#6b7280;font-size:0.72rem;line-height:1.6'>"
            "🤖 <b>EyeAmHere</b> v1.0<br>"
            "AI Buildathon 2026<br>"
            "<span style='color:#3b82f6'>● Face Recognition</span> "
            "<span style='color:#10b981'>● Liveness</span> "
            "<span style='color:#f59e0b'>● AI Insights</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    
    def _render_dashboard_overview(self):
        """Render dashboard overview with safe error handling"""
        try:
            # Get today's stats with safe error handling
            stats = self._get_safe_attendance_stats()
            
            attendance_rate = stats.get('attendance_rate', 0)

            # Key metrics row - Premium stat cards
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                PremiumTheme.render_stat_card(
                    label="Total Students",
                    value=str(stats.get("total_students", 0)),
                    icon="👥",
                    card_type="primary"
                )
            
            with col2:
                PremiumTheme.render_stat_card(
                    label="Present Today",
                    value=str(stats.get("present_today", 0)),
                    icon="✅",
                    card_type="success"
                )
            
            with col3:
                PremiumTheme.render_stat_card(
                    label="Absent Today",
                    value=str(stats.get("absent_today", 0)),
                    icon="❌",
                    card_type="warning"
                )
            
            with col4:
                PremiumTheme.render_stat_card(
                    label="Attendance Rate",
                    value=f"{attendance_rate:.1f}%",
                    icon="📊",
                    card_type="info"
                )
            
            # Weekly trend if available
            weekly_rate = stats.get('avg_weekly_rate', 0)
            if weekly_rate > 0:
                trend_delta = attendance_rate - weekly_rate
                if trend_delta > 5:
                    st.success(f"📈 Attendance up {trend_delta:+.1f}% vs weekly average!")
                elif trend_delta < -5:
                    st.warning(f"📉 Attendance down {trend_delta:+.1f}% vs weekly average")
                else:
                    st.info(f"➡️ Attendance stable ({trend_delta:+.1f}% vs weekly average)")
            
            st.markdown("---")
            
            # Today's activity
            col1, col2 = st.columns([2, 1])
            
            with col1:
                PremiumTheme.render_section_header("Today's Attendance", icon="📅")
                self._render_safe_attendance_records()
            
            with col2:
                PremiumTheme.render_section_header("Quick Actions", icon="🎯")
                self._render_quick_actions()
                
                # System status
                st.markdown("---")
                PremiumTheme.render_section_header("System Status", icon="📊")
                self._render_system_status()
                
        except Exception as e:
            logger.error(f"Error rendering dashboard overview: {e}")
            st.error(f"❌ Dashboard error: {str(e)}")
            self._render_fallback_dashboard()
    
    def _get_safe_attendance_stats(self) -> Dict:
        """Get attendance stats with safe error handling"""
        try:
            if self.attendance_service:
                stats = self.attendance_service.get_today_attendance_summary()
                if stats:
                    return stats
            
            # Fallback to direct database query
            return self._get_basic_stats_from_db()
            
        except Exception as e:
            logger.error(f"Error getting attendance stats: {e}")
            return {
                'total_students': 0,
                'present_today': 0,
                'absent_today': 0,
                'attendance_rate': 0
            }
    
    def _get_basic_stats_from_db(self) -> Dict:
        """Get basic stats directly from database"""
        try:
            from database.connection import get_db_connection
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Total students
                cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
                total_students = cursor.fetchone()[0]
                
                # Present today
                cursor.execute("""
                    SELECT COUNT(DISTINCT student_id) 
                    FROM attendance 
                    WHERE date = ? AND time_in IS NOT NULL
                """, (str(date.today()),))
                present_today = cursor.fetchone()[0]
                
                absent_today = max(0, total_students - present_today)
                attendance_rate = (present_today / total_students * 100) if total_students > 0 else 0
                
                return {
                    'total_students': total_students,
                    'present_today': present_today,
                    'absent_today': absent_today,
                    'attendance_rate': round(attendance_rate, 1)
                }
                
        except Exception as e:
            logger.error(f"Error getting basic stats: {e}")
            return {}
    
    def _render_safe_attendance_records(self):
        """Render attendance records with safe error handling"""
        try:
            # Try to get today's records
            today_records = self._get_safe_attendance_records()
            
            if today_records and len(today_records) > 0:
                # Create DataFrame safely
                df = pd.DataFrame(today_records)
                
                # Ensure we have the required columns
                required_columns = ['name', 'roll_number', 'time_in', 'time_out']
                available_columns = [col for col in required_columns if col in df.columns]
                
                if available_columns:
                    display_df = df[available_columns].head(10)
                    
                    # Format time columns if they exist
                    for time_col in ['time_in', 'time_out']:
                        if time_col in display_df.columns:
                            display_df[time_col] = display_df[time_col].fillna('Not marked')
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "name": "Student Name",
                            "roll_number": "Roll Number",
                            "time_in": "Check In",
                            "time_out": "Check Out"
                        }
                    )
                else:
                    st.info("📝 No attendance column data available")
            else:
                st.info("No attendance records for today yet")
                
        except Exception as e:
            logger.error(f"Error rendering attendance records: {e}")
            st.warning("⚠️ Could not load today's attendance records")
    
    def _get_safe_attendance_records(self) -> List[Dict]:
        """Get attendance records with safe error handling"""
        try:
            if self.attendance_service:
                records = self.attendance_service.get_attendance_records(
                    start_date=date.today(),
                    end_date=date.today()
                )
                if records:
                    return records
            
            # Fallback to direct database query
            return self._get_basic_attendance_records()
            
        except Exception as e:
            logger.error(f"Error getting safe attendance records: {e}")
            return []
    
    def _get_basic_attendance_records(self) -> List[Dict]:
        """Get basic attendance records from database"""
        try:
            from database.connection import get_db_connection
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        s.name,
                        s.roll_number, 
                        a.time_in,
                        a.time_out,
                        a.status
                    FROM attendance a
                    JOIN students s ON a.student_id = s.id
                    WHERE a.date = ?
                    ORDER BY a.created_at DESC
                    LIMIT 10
                """, (str(date.today()),))
                
                records = []
                for row in cursor.fetchall():
                    records.append({
                        'name': row['name'],
                        'roll_number': row['roll_number'],
                        'time_in': row['time_in'] or 'Not marked',
                        'time_out': row['time_out'] or 'Not marked',
                        'status': row['status']
                    })
                
                return records
                
        except Exception as e:
            logger.error(f"Error getting basic attendance records: {e}")
            return []
    
    def _render_quick_actions(self):
        """Render quick action buttons"""
        if st.button("📷 Start Attendance", use_container_width=True, type="primary", key="dashboard_start_attendance"):
            st.session_state.current_page = "Mark Attendance"
            st.rerun()
        
        if st.button("📝 View All Records", use_container_width=True, key="dashboard_view_records"):
            st.session_state.current_page = "Attendance Records"
            st.rerun()

        if st.button("➕ Add New Student", use_container_width=True, key="dashboard_add_student"):
            st.session_state.current_page = "Student Management"
            st.rerun()
        
        if st.button("📊 View Analytics", use_container_width=True, key="dashboard_view_analytics"):
            st.session_state.current_page = "Analytics"
            st.rerun()

        if st.button("🎥 Live Mask Check", use_container_width=True, key="dashboard_live_mask"):
            st.session_state.current_page = "Live Mask Detection"
            st.rerun()

        if st.button("🩺 System health", use_container_width=True, key="dashboard_health"):
            st.session_state.current_page = "System Health"
            st.rerun()
    
    def _render_system_status(self):
        """Render system status information"""
        try:
            from config.settings import get_config_value, DB_FILE

            smtp_on = str(get_config_value("SMTP_ENABLED", "false")).lower() in (
                "1", "true", "yes", "on",
            )
            st.caption(f"**Database:** `{DB_FILE}`")
            st.caption(
                "**Email (password reset):** "
                + ("configured (SMTP enabled)" if smtp_on else "in-app token only — set `SMTP_ENABLED=true` in `.env` to send mail")
            )

            if self.student_service:
                student_stats = self.student_service.get_student_statistics()
                
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Courses", len(student_stats.get('by_course', {})))
                with c2:
                    st.metric("Students with photos", student_stats.get('with_photos', 0))
            else:
                from database.connection import get_db_connection
                
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT COUNT(DISTINCT course) FROM students WHERE is_active = 1")
                    course_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(DISTINCT student_id) FROM face_embeddings")
                    photo_count = cursor.fetchone()[0]
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Courses", course_count)
                    with c2:
                        st.metric("Students with photos", photo_count)
                    
        except Exception as e:
            logger.error(f"Error rendering system status: {e}")
            st.warning("System status unavailable")
    
    def _render_user_dashboard_content(self):
        """Render user dashboard content"""
        st.markdown("## 📊 Today's Overview")
        
        try:
            stats = self._get_safe_attendance_stats()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👥 Total Students", stats.get('total_students', 0))
            
            with col2:
                present_today = stats.get('present_today', 0)
                absent_today = stats.get('absent_today', 0)
                st.metric("✅ Present Today", present_today, delta=f"{absent_today} absent")
            
            with col3:
                today_rate = stats.get('attendance_rate', 0)
                st.metric("📊 Attendance Rate", f"{today_rate:.1f}%")
            
            with col4:
                st.metric("📅 Today", date.today().strftime('%B %d, %Y'))
            
            # Recent attendance
            st.markdown("### 🕐 Recent Attendance")
            self._render_safe_attendance_records()
            
        except Exception as e:
            logger.error(f"Error rendering user dashboard: {e}")
            st.error(f"❌ Error loading dashboard: {str(e)}")
    
    def _render_fallback_dashboard(self):
        """Render basic fallback dashboard when main dashboard fails"""
        st.warning("⚠️ Dashboard experiencing issues. Showing basic information.")
        
        try:
            from database.connection import get_db_connection
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM students WHERE is_active = 1")
                student_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ?", (str(date.today()),))
                attendance_count = cursor.fetchone()[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📚 Total Students", student_count)
                with col2:
                    st.metric("📋 Today's Records", attendance_count)
                
                # Quick actions
                st.markdown("### 🎯 Quick Actions")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("👥 Students", key="fallback_students"):
                        st.session_state.current_page = "Student Management"
                        st.rerun()
                
                with col2:
                    if st.button("📷 Attendance", key="fallback_attendance"):
                        st.session_state.current_page = "Mark Attendance"
                        st.rerun()
                
                with col3:
                    if st.button("📊 Records", key="fallback_records"):
                        st.session_state.current_page = "Attendance Records"
                        st.rerun()
                
        except Exception as e:
            st.error(f"❌ Critical error: {str(e)}")
            st.info("💡 Try restarting the application or check your database connection")
    
    def _render_attendance_records(self):
        """Render attendance records page"""
        st.markdown("## 📝 Attendance Records")
        
        try:
            # Date range selector
            col1, col2, col3 = st.columns(3)
            
            with col1:
                start_date = st.date_input("📅 Start Date", value=date.today() - timedelta(days=7))
            
            with col2:
                end_date = st.date_input("📅 End Date", value=date.today())
            
            with col3:
                if st.button("🔍 Filter Records", use_container_width=True):
                    st.rerun()
            
            # Get records
            if self.attendance_service:
                records = self.attendance_service.get_attendance_records(start_date, end_date)
            else:
                records = self._get_attendance_records_fallback(start_date, end_date)
            
            if records:
                # Display as DataFrame
                df = pd.DataFrame(records)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Export option
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"attendance_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
            else:
                st.info("📝 No records found for the selected date range")
                
        except Exception as e:
            logger.error(f"Error rendering attendance records: {e}")
            st.error(f"❌ Error loading records: {str(e)}")
    
    def _get_attendance_records_fallback(self, start_date: date, end_date: date) -> List[Dict]:
        """Fallback method to get attendance records"""
        try:
            from database.connection import get_db_connection
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        s.name as student_name,
                        s.roll_number,
                        s.course,
                        a.date,
                        a.time_in,
                        a.time_out,
                        a.status,
                        a.marked_by
                    FROM attendance a
                    JOIN students s ON a.student_id = s.id
                    WHERE a.date BETWEEN ? AND ?
                    ORDER BY a.date DESC, a.time_in DESC
                """, (str(start_date), str(end_date)))
                
                records = []
                for row in cursor.fetchall():
                    records.append(dict(row))
                
                return records
                
        except Exception as e:
            logger.error(f"Error getting attendance records fallback: {e}")
            return []
    
    def _render_user_management(self):
        """Render user management page"""
        st.markdown("## 👤 User Management")
        
        try:
            # Add new user section
            with st.expander("➕ Add New User"):
                with st.form("add_user_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        new_email = st.text_input("📧 Email")
                        new_password = st.text_input("🔒 Password", type="password")
                    
                    with col2:
                        new_role = st.selectbox("👤 Role", ["user", "admin"])
                        confirm_password = st.text_input("🔒 Confirm Password", type="password")
                    
                    if st.form_submit_button("➕ Add User"):
                        if new_password == confirm_password:
                            try:
                                from auth.user_service import UserService
                                user_service = UserService()
                                success, message = user_service.create_user(new_email, new_password, new_role)
                                
                                if success:
                                    st.success(f"✅ User {new_email} added successfully!")
                                else:
                                    st.error(f"❌ Error: {message}")
                            except Exception as e:
                                st.error(f"❌ Error adding user: {str(e)}")
                        else:
                            st.error("❌ Passwords do not match")
            
            # Existing users
            st.markdown("### 👥 Current Users")
            
            try:
                from database.connection import get_db_connection
                
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, email, role, created_at FROM users ORDER BY created_at DESC")
                    users = cursor.fetchall()
                
                if users:
                    users_df = pd.DataFrame(users)
                    st.dataframe(users_df, use_container_width=True, hide_index=True)
                else:
                    st.info("👤 No users found")
                    
            except Exception as e:
                st.error(f"❌ Error loading users: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in user management: {e}")
            st.error(f"❌ User management error: {str(e)}")
    
    def _render_danger_zone(self):
        """Render danger zone page"""
        st.markdown("## ⚠️ Danger Zone")
        st.error("🚨 **Warning:** These actions are irreversible and require admin re-authentication.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🗑️ Delete All Data")
            st.warning("This will delete ALL students, attendance records, and face data")

            delete_phrase = st.text_input(
                "Type DELETE STUDENTS to confirm",
                key="danger_delete_phrase",
                placeholder="DELETE STUDENTS",
            )
            delete_password = st.text_input(
                "Admin password",
                type="password",
                key="danger_delete_password",
            )

            if st.button("🗑️ Delete All Students", type="secondary", key="danger_delete_all_students"):
                authorized, message = self._authorize_danger_action(
                    delete_password,
                    delete_phrase,
                    "DELETE STUDENTS",
                )
                if not authorized:
                    st.error(message)
                    return

                success, message = self._delete_all_student_data()
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
        
        with col2:
            st.markdown("### 📊 Reinitialize System Schema")
            st.info("Re-runs database initialization. Existing data is preserved.")

            reset_phrase = st.text_input(
                "Type REINITIALIZE SCHEMA to confirm",
                key="danger_reset_phrase",
                placeholder="REINITIALIZE SCHEMA",
            )
            reset_password = st.text_input(
                "Admin password",
                type="password",
                key="danger_reset_password",
            )

            if st.button("🔄 Reinitialize Schema", type="secondary", key="danger_reset_schema"):
                authorized, message = self._authorize_danger_action(
                    reset_password,
                    reset_phrase,
                    "REINITIALIZE SCHEMA",
                )
                if not authorized:
                    st.error(message)
                    return

                try:
                    from database.connection import init_database

                    init_database()
                    self._audit_danger_action("danger_reinitialize_schema")
                    st.success("✅ Database schema reinitialized successfully")
                except Exception as e:
                    st.error(f"❌ Error reinitializing schema: {str(e)}")

        st.markdown("---")
        st.markdown("### 🧬 Biometric Retention")
        st.info(
            "Deletes stored face embeddings for inactive students that are outside "
            "the configured retention window. Attendance rows and inactive student "
            "metadata are preserved."
        )
        purge_phrase = st.text_input(
            "Type PURGE BIOMETRICS to confirm",
            key="danger_purge_biometrics_phrase",
            placeholder="PURGE BIOMETRICS",
        )
        purge_password = st.text_input(
            "Admin password",
            type="password",
            key="danger_purge_biometrics_password",
        )
        if st.button("🧬 Purge Expired Biometrics", type="secondary", key="danger_purge_biometrics"):
            authorized, message = self._authorize_danger_action(
                purge_password,
                purge_phrase,
                "PURGE BIOMETRICS",
            )
            if not authorized:
                st.error(message)
                return

            try:
                if not self.student_service:
                    st.error("Student service is unavailable.")
                    return
                count, message = self.student_service.purge_inactive_biometrics()
                self._audit_danger_action(
                    "danger_purge_expired_biometrics",
                    {"deleted_embeddings": count},
                )
                if count:
                    st.success(f"✅ {message}")
                else:
                    st.info(message)
            except Exception as e:
                st.error(f"❌ Error purging biometrics: {str(e)}")

    def _authorize_danger_action(
        self,
        password: str,
        typed_phrase: str,
        expected_phrase: str,
    ) -> Tuple[bool, str]:
        """Require typed confirmation and current admin password for dangerous actions."""
        if typed_phrase != expected_phrase:
            return False, f"Type `{expected_phrase}` exactly to confirm."
        if not password:
            return False, "Enter your admin password to continue."

        actor = self.session_manager.get_current_user() or {}
        email = actor.get("email")
        if not email:
            return False, "Could not identify the current admin session."

        try:
            from auth.authentication import AuthenticationService

            auth = AuthenticationService()
            user = auth.user_repo.get_user_by_email(email)
            if not user or user.get("role") != "admin":
                return False, "Only admins can perform this action."
            if not auth.verify_password(password, user["password_hash"]):
                return False, "Admin password is incorrect."
            return True, "Authorized"
        except Exception as e:
            logger.error("Danger action authorization failed: %s", e)
            return False, "Could not verify admin password."

    def _delete_all_student_data(self) -> Tuple[bool, str]:
        """Delete all student, embedding, and attendance data through the service layer."""
        try:
            if not self.student_service:
                return False, "Student service is unavailable."

            success, message = self.student_service.delete_all_students()
            if success:
                self._audit_danger_action(
                    "danger_delete_all_student_data",
                    {"tables": ["face_embeddings", "attendance", "students"]},
                )
                return True, f"✅ {message}"
            return False, f"❌ {message}"
        except Exception as e:
            logger.error("Danger delete all failed: %s", e)
            return False, f"❌ Error deleting data: {str(e)}"

    def _audit_danger_action(self, action: str, detail: Optional[Dict] = None) -> None:
        """Best-effort audit logging for destructive admin actions."""
        try:
            from services.audit_service import log as audit_log

            actor = self.session_manager.get_current_user()
            audit_log(
                action,
                actor_email=(actor or {}).get("email"),
                detail=detail or {},
            )
        except Exception:
            pass
