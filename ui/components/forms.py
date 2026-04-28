"""
Reusable form components
Extracted from app.py form creation functions
"""
import streamlit as st
from typing import Dict, List, Optional, Tuple, Any
from auth.validators import validate_email, validate_password, validate_username

class LoginForm:
    """Login form component"""
    
    @staticmethod
    def render() -> Tuple[Optional[str], Optional[str], bool]:
        """Render login form and return email, password, submit status"""
        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="Enter your email")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns(2)
            with col1:
                login_clicked = st.form_submit_button("🚀 Login", use_container_width=True)
            with col2:
                forgot_clicked = st.form_submit_button("🔑 Forgot Password", use_container_width=True)
        
        if forgot_clicked:
            st.session_state.goto_forgot_password = True
            st.rerun()

        if login_clicked and email and password:
            return email.strip(), password, True

        if login_clicked and (not email or not password):
            st.warning("Enter email and password to sign in.")

        return None, None, False

class SignupForm:
    """Signup form component"""
    
    @staticmethod
    def render() -> Tuple[Optional[Dict], bool]:
        """Render signup form and return user data dict, submit status"""
        st.subheader("📝 Create Account")
        
        with st.form("signup_form"):
            username = st.text_input("👤 Username", placeholder="Choose a username")
            email = st.text_input("📧 Email", placeholder="Enter your email")
            password = st.text_input("🔒 Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
            
            signup_clicked = st.form_submit_button("✨ Create Account", use_container_width=True)
        
        if signup_clicked:
            # Validate inputs
            errors = []
            
            if not validate_email(email):
                errors.append("Invalid email format")
            
            username_valid, username_msg = validate_username(username)
            if not username_valid:
                errors.append(username_msg)
            
            password_valid, password_msg = validate_password(password)
            if not password_valid:
                errors.append(password_msg)
            
            if password != confirm_password:
                errors.append("Passwords do not match")
            
            if errors:
                for error in errors:
                    st.error(error)
                return None, False
            
            user_data = {
                'username': username.strip(),
                'email': email.strip().lower(),
                'password': password
            }
            
            return user_data, True
        
        return None, False

class StudentForm:
    """Student registration form component"""
    
    @staticmethod
    def render() -> Tuple[Optional[Dict], Optional[List], bool]:
        """Render student form and return student data, images, submit status"""
        st.subheader("👨‍🎓 Add New Student")
        
        with st.form("student_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name", placeholder="Enter student's full name")
                roll_number = st.text_input("Roll Number", placeholder="Enter roll number")
                email = st.text_input("Email", placeholder="Enter email address")
            
            with col2:
                phone = st.text_input("Phone", placeholder="Enter phone number")
                course = st.selectbox("Course", 
                                    ["CSE", "CE", "EE", "BE", "ME"], 
                                    help="Select the student's course")
            
            st.markdown("### 📷 Upload Student Photos")
            st.info("Upload 2-5 clear photos of the student for better recognition accuracy")
            
            uploaded_files = st.file_uploader(
                "Choose photos",
                type=['png', 'jpg', 'jpeg'],
                accept_multiple_files=True,
                help="Upload 2-5 clear photos showing the student's face"
            )
            
            submit_clicked = st.form_submit_button("✅ Add Student", use_container_width=True)
        
        if submit_clicked:
            # Validate inputs
            errors = []
            
            if not name.strip():
                errors.append("Student name is required")
            if not roll_number.strip():
                errors.append("Roll number is required")
            if not validate_email(email):
                errors.append("Valid email is required")
            if not uploaded_files or len(uploaded_files) < 2:
                errors.append("At least 2 photos are required")
            if uploaded_files and len(uploaded_files) > 5:
                errors.append("Maximum 5 photos allowed")
            
            if errors:
                for error in errors:
                    st.error(error)
                return None, None, False
            
            student_data = {
                'name': name.strip(),
                'roll_number': roll_number.strip().upper(),
                'email': email.strip().lower(),
                'phone': phone.strip(),
                'course': course
            }
            
            return student_data, uploaded_files, True
        
        return None, None, False

class AttendanceForm:
    """Attendance marking form component"""
    
    @staticmethod
    def render_camera_input() -> Optional[Any]:
        """Render camera input for attendance"""
        st.subheader("📷 Mark Attendance")
        st.caption(
            "YOLO checks the captured photo for a face mask. Remove your mask before taking the picture — masked faces are blocked."
        )

        col1, col2 = st.columns([2, 1])

        with col1:
            camera_input = st.camera_input("Take a photo to mark attendance")
        
        with col2:
            if camera_input is not None:
                st.image(camera_input, caption="Captured Image", width=200)
        
        return camera_input
    
    @staticmethod
    def render_file_upload() -> Optional[Any]:
        """Render file upload for attendance"""
        st.subheader("📁 Upload Photo for Attendance")
        
        uploaded_file = st.file_uploader(
            "Choose a photo",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear photo showing the face"
        )
        
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Uploaded Image", width=300)
        
        return uploaded_file

class FilterForm:
    """Reusable filter form for data display"""
    
    @staticmethod
    def render_date_filter() -> Tuple[Any, Any]:
        """Render date range filter"""
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")
        
        return start_date, end_date
    
    @staticmethod
    def render_student_filter(students: List[Dict]) -> Optional[int]:
        """Render student selection filter"""
        if not students:
            st.warning("No students available")
            return None
        
        student_options = {f"{s['name']} ({s['roll_number']})": s['id'] for s in students}
        selected_option = st.selectbox(
            "Select Student",
            options=["All Students"] + list(student_options.keys())
        )
        
        if selected_option == "All Students":
            return None
        else:
            return student_options[selected_option]
    
    @staticmethod
    def render_course_filter() -> Optional[str]:
        """Render course selection filter"""
        course = st.selectbox(
            "Filter by Course",
            options=["All Courses", "CSE", "CE", "EE", "BE", "ME"]
        )
        
        return None if course == "All Courses" else course

class SearchForm:
    """Search form component"""
    
    @staticmethod
    def render(placeholder: str = "Search...") -> Optional[str]:
        """Render search input"""
        search_term = st.text_input(
            "🔍 Search",
            placeholder=placeholder,
            help="Search by name, roll number, or email"
        )
        
        return search_term.strip() if search_term else None
