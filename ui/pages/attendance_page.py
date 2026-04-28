"""
Attendance marking page component - Enhanced with debugging
Extracted from app.py attendance functionality
"""
import time
import streamlit as st
import cv2
import numpy as np
import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Optional, Dict, Tuple
from services.attendance_service import AttendanceService
from config.settings import RECOGNITION_THRESHOLD, RECOGNITION_MARGIN
from config.settings import FOCUS_MONITORING_ENABLED
from ui.components.forms import AttendanceForm
from ui.components.layout import render_page_header, section_title, card_container
from ui.theme import PremiumTheme

logger = logging.getLogger(__name__)

class AttendancePage:
    """Enhanced attendance marking page with debug capabilities"""
    
    def __init__(self):
        self.attendance_service = AttendanceService()
        try:
            from face_focus.focus_energy_service import FocusEnergyService

            self.focus_service = FocusEnergyService()
        except Exception as e:
            logger.error("Error initializing focus service: %s", e)
            self.focus_service = None
    
    def render(self):
        """Render attendance marking page"""
        render_page_header(
            title="Live Face Attendance",
            subtitle="Use the camera or upload a photo to mark IN/OUT attendance in real time.",
            icon="📷",
        )
        
        # Add debug mode toggle
        debug_mode = st.checkbox("🔍 Enable Recognition Debug Mode", 
                               help="Show detailed analysis when face recognition fails")
        
        # Instructions
        self._render_instructions()
        self._render_recognition_calibration()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            with card_container():
                section_title("Camera & Upload", icon="🎥")
                self._render_camera_section(debug_mode)
        
        with col2:
            with card_container():
                section_title("Today's Summary", icon="📊")
                self._render_summary_section()
    
    def _render_instructions(self):
        """Render usage instructions"""
        with st.expander("📋 How to Use", expanded=False):
            st.markdown("""
            **For best results:**
            - ✅ Ensure good lighting
            - ✅ Look directly at the camera
            - ✅ Keep your face clearly visible
            - ✅ Remove any obstructions (mask, hand, etc.)
            - ✅ Stay still when taking the photo
            - ✅ Use similar angle as registration photos
            - 🧠 Watch the focus alert if the system says your face is off-center or blurry
            
            **System automatically detects:**
            - 🟢 **IN** - When entering college
            - 🔴 **OUT** - When leaving college
            
            **Live mask check (WebRTC):** Use sidebar **Live Mask Detection** for a real-time mask preview (separate from attendance marking).
            
            **If recognition fails:**
            - 🔍 Enable debug mode for detailed analysis
            - 📸 Try taking another photo with better lighting
            - 📐 Use similar distance and angle as registration
            """)
    
    def _render_camera_section(self, debug_mode: bool = False):
        """Render camera input section"""
        # Camera input using form component
        camera_input = AttendanceForm.render_camera_input()
        
        if camera_input is not None:
            self._process_attendance_image(camera_input, debug_mode, source="camera")
        
        st.markdown("---")
        
        # Alternative file upload
        uploaded_file = AttendanceForm.render_file_upload()
        
        if uploaded_file is not None:
            self._process_attendance_image(uploaded_file, debug_mode, source="upload")
    
    def _render_summary_section(self):
        """Render today's summary section"""
        st.markdown("### 📊 Today's Summary")
        
        try:
            stats = self.attendance_service.get_today_attendance_summary()
            
            st.metric("👥 Total", stats.get('total_students', 0))
            st.metric("✅ Present", stats.get('present_today', 0))
            st.metric("📈 Rate", f"{stats.get('attendance_rate', 0):.1f}%")
            
            # Recent entries
            st.markdown("### 🕐 Recent Activity")
            
            recent_records = self.attendance_service.get_attendance_records(
                start_date=date.today(),
                end_date=date.today()
            )
            
            if recent_records:
                # Show last 5 records
                for record in recent_records[-5:]:
                    with st.container():
                        st.write(f"👤 {record['student_name']}")
                        st.write(f"⏰ {record['time_in'] or 'N/A'}")
                        st.divider()
            else:
                st.info("No activity yet today")
                
        except Exception as e:
            logger.error(f"Error rendering summary: {e}")
            st.error(f"Error: {str(e)}")
    
    def _process_attendance_image(self, image_input, debug_mode: bool = False, source: str = "camera"):
        """Process attendance marking from image with proper format handling"""
        
        # Step 1: Convert image to proper format
        with st.spinner("🔧 Converting image format..."):
            processed_image = self._convert_image_input(image_input, debug_mode)
            
            if processed_image is None:
                st.error("❌ Failed to process image format")
                if debug_mode:
                    st.error("🔧 Image conversion failed - check image format and try again")
                return
            
            if debug_mode:
                st.success(f"✅ Image converted successfully: {processed_image.shape}, dtype: {processed_image.dtype}")

        # Step 1.5: Liveness / anti-spoofing check (passive, non-blocking)
        try:
            from face_recognition.liveness_detector import compute_liveness_score
            liveness = compute_liveness_score(processed_image)
            st.session_state["_liveness_result"] = liveness
        except Exception as _le:
            logger.warning("Liveness detection unavailable: %s", _le)
            st.session_state["_liveness_result"] = None

        # Step 2: Check user focus / energy before recognition
        if FOCUS_MONITORING_ENABLED and self.focus_service is not None:
            with st.spinner("🧠 Checking focus and energy..."):
                try:
                    focus_result = self.focus_service.analyze_image(processed_image)
                    self._show_focus_result(focus_result, debug_mode)
                except Exception as e:
                    logger.error("Focus analysis error: %s", e)
                    if debug_mode:
                        st.warning(f"Focus analysis unavailable: {e}")

        # Step 2.5: Proxy / impersonation detection — flag multiple faces
        try:
            from face_recognition.image_utils import count_faces_in_image
            face_count = count_faces_in_image(processed_image)
            if face_count > 1:
                st.error(
                    f"⚠️ **Proxy Attendance Detected!** "
                    f"{face_count} faces found in the frame. "
                    "Only one person may mark attendance at a time."
                )
                try:
                    from database.audit_repository import append_audit
                    actor = st.session_state.get("user_email", "unknown")
                    append_audit(
                        action="proxy_attempt_blocked",
                        actor_email=actor,
                        target_type="attendance",
                        target_id=None,
                        detail=f"Multiple faces detected: {face_count} faces in frame",
                        client_hint=source,
                    )
                except Exception:
                    pass
                return
        except Exception as e:
            logger.warning("Proxy detection error: %s", e)

        # Step 3: Block attendance if face covering (mask) is detected
        with st.spinner("🎭 Checking face covering..."):
            try:
                from face_mask.mask_gate import check_face_uncovered_for_attendance

                allowed, mask_msg, mask_detail = check_face_uncovered_for_attendance(processed_image)
                if not allowed:
                    st.error("🚫 Attendance blocked")
                    st.warning(mask_msg)
                    if debug_mode and mask_detail:
                        with st.expander("Mask check details", expanded=True):
                            st.json(mask_detail)
                    return
                if debug_mode and mask_detail and not mask_detail.get("skipped"):
                    st.caption(f"Covering check: {mask_msg}")
            except Exception as e:
                logger.error("Mask gate error: %s", e)
                st.error("Face covering check failed. Please try again or contact an admin.")
                if debug_mode:
                    st.exception(e)
                return

        # Step 4: Process face recognition
        with st.spinner("🔍 Processing face recognition..."):
            try:
                # Recognize student and mark attendance
                success, message, student_info = self.attendance_service.mark_attendance_by_recognition(
                    processed_image,  # Use processed image
                    marked_by=f"face_recognition_{source}"
                )
                
                if success and student_info:
                    self._show_recognition_success(student_info, message)
                else:
                    self._show_recognition_failure(message, processed_image, debug_mode)
                    
            except Exception as e:
                logger.error(f"Error processing attendance: {e}")
                st.error(f"❌ Error: {str(e)}")
                
                if debug_mode:
                    with st.expander("🔧 Technical Error Details"):
                        st.exception(e)
    
    def _convert_image_input(self, image_input, debug_mode: bool = False) -> Optional[np.ndarray]:
        """Convert various image inputs to OpenCV format"""
        try:
            processed_image = None
            
            # Handle different input types
            if hasattr(image_input, 'read'):
                # File upload case
                if debug_mode:
                    st.info(f"Processing uploaded file: {image_input.name}")
                
                file_bytes = image_input.read()
                nparr = np.frombuffer(file_bytes, np.uint8)
                processed_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
            elif hasattr(image_input, 'getvalue'):
                # Camera input case
                if debug_mode:
                    st.info("Processing camera input")
                
                file_bytes = image_input.getvalue()
                nparr = np.frombuffer(file_bytes, np.uint8)
                processed_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
            elif isinstance(image_input, np.ndarray):
                # Already numpy array
                processed_image = image_input.copy()
                
            else:
                if debug_mode:
                    st.error(f"Unsupported image input type: {type(image_input)}")
                logger.error(f"Unsupported image input type: {type(image_input)}")
                return None
            
            # Validate the processed image
            if processed_image is None:
                if debug_mode:
                    st.error("❌ Failed to decode image")
                return None
            
            # Ensure proper format
            if processed_image.dtype != np.uint8:
                if debug_mode:
                    st.info(f"Converting from {processed_image.dtype} to uint8")
                processed_image = self._ensure_uint8(processed_image)
            
            # Ensure 3 channels (BGR)
            if len(processed_image.shape) == 2:
                if debug_mode:
                    st.info("Converting grayscale to BGR")
                processed_image = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2BGR)
            elif len(processed_image.shape) == 3:
                if processed_image.shape[2] == 4:
                    if debug_mode:
                        st.info("Converting RGBA to BGR")
                    processed_image = cv2.cvtColor(processed_image, cv2.COLOR_RGBA2BGR)
                elif processed_image.shape[2] == 1:
                    if debug_mode:
                        st.info("Converting single channel to BGR")
                    processed_image = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2BGR)
            
            # Final validation
            if not self._validate_opencv_image(processed_image):
                if debug_mode:
                    st.error("❌ Final image validation failed")
                return None
            
            return processed_image
            
        except Exception as e:
            logger.error(f"Error converting image: {e}")
            if debug_mode:
                st.error(f"❌ Image conversion error: {str(e)}")
            return None
    
    def _ensure_uint8(self, image: np.ndarray) -> np.ndarray:
        """Ensure image is in uint8 format"""
        try:
            if image.dtype == np.uint8:
                return image
            
            if image.dtype in [np.float32, np.float64]:
                if image.max() <= 1.0:
                    return (image * 255).astype(np.uint8)
                else:
                    return np.clip(image, 0, 255).astype(np.uint8)
            else:
                return np.clip(image, 0, 255).astype(np.uint8)
                
        except Exception as e:
            logger.error(f"Error converting to uint8: {e}")
            return image
    
    def _validate_opencv_image(self, image) -> bool:
        """Validate image for OpenCV operations"""
        try:
            if image is None:
                return False
            
            if not isinstance(image, np.ndarray):
                return False
            
            if len(image.shape) not in [2, 3]:
                return False
            
            if len(image.shape) == 3 and image.shape[2] not in [1, 3]:
                return False
            
            if image.size == 0:
                return False
            
            return True
            
        except:
            return False

    def _show_focus_result(self, focus_result: Dict, debug_mode: bool = False) -> None:
        """Show focus and energy feedback before attendance recognition."""
        score = float(focus_result.get("focus_score", 0.0))
        status = focus_result.get("status", "critical")

        if status == "focused":
            st.success(f"🧠 Focus score {score:.1f}/100 - good signal.")
        elif status == "attention":
            st.warning(f"🧠 Focus score {score:.1f}/100 - user may need to adjust posture or lighting.")
        else:
            st.error(f"🧠 Focus score {score:.1f}/100 - low focus detected.")

        alerts = focus_result.get("alerts", [])
        for alert in alerts:
            st.caption(f"• {alert}")

        if debug_mode:
            with st.expander("Focus analysis details", expanded=False):
                st.json(focus_result)
    
    def _show_recognition_success(self, student_info: Dict, message: str):
        """Show successful recognition and attendance marking"""
        st.success(f"👋 Welcome, **{student_info['name']}**!")
        
        # Student information
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.info(f"🎫 Roll: {student_info['roll_number']}")
            if 'course' in student_info:
                st.info(f"📚 Course: {student_info['course']}")
        
        with col_info2:
            confidence = student_info.get('recognition_confidence', 0)
            st.info(f"📊 Match score: {confidence:.3f}")
            margin = student_info.get("recognition_margin")
            runner = student_info.get("runner_up_similarity")
            if margin is not None and runner is not None:
                st.caption(f"Margin vs next student: {margin:.3f} (next: {runner:.3f})")
        
        # ── Liveness score badge ──────────────────────────────────────
        liveness = st.session_state.get("_liveness_result")
        if liveness is not None:
            score = liveness.score
            label = liveness.label
            if label == "Live":
                icon, colour = "🔒", "green"
            elif label == "Suspicious":
                icon, colour = "⚠️", "orange"
            else:
                icon, colour = "🚫", "red"
            st.markdown(
                f"<span style='color:{colour};font-weight:600'>"
                f"{icon} Liveness: {score:.0f}% — {label} face confirmed</span>",
                unsafe_allow_html=True,
            )

        # Attendance status
        st.success(f"✅ {message}")
        
        # Show today's complete status for this student
        self._show_student_daily_status(student_info['student_id'])
        
        # Celebration
        st.balloons()
    
    def _show_recognition_failure(self, message: str, image, debug_mode: bool = False):
        """Show recognition failure with optional debug analysis"""
        st.error("❌ Face not recognized")
        st.warning(f"Details: {message}")
        
        if debug_mode:
            st.markdown("---")
            
            # Show image analysis
            try:
                self._show_debug_analysis(image)
            except Exception as e:
                st.error(f"Debug analysis failed: {e}")
            
            # Quick fix suggestions
            st.markdown("### 🛠️ Quick Fixes")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👥 View Students", key="view_students_btn", help="Check registered students"):
                    st.session_state.current_page = "Student Management"
                    st.rerun()
            
            with col2:
                if st.button("📝 Manual Entry", key="manual_entry_btn", help="Mark attendance manually"):
                    self._show_manual_entry_form()
            st.caption(
                f"Tuning: set RECOGNITION_THRESHOLD (now {RECOGNITION_THRESHOLD}) and "
                f"RECOGNITION_MARGIN (now {RECOGNITION_MARGIN}) in your environment or `.env`."
            )
        else:
            # Standard troubleshooting without debug
            st.info("""
            💡 **Troubleshooting:**
            - Ensure good lighting
            - Look directly at camera  
            - Remove any face coverings
            - Try repositioning yourself
            - Make sure you are registered in the system
            - Enable debug mode for detailed analysis
            """)

    def _render_recognition_calibration(self):
        """Show the active recognition decision settings."""
        with st.expander("🎯 Recognition Calibration", expanded=False):
            st.markdown(
                f"""
                The attendance decision uses **cosine similarity** from the best registered
                template per student.

                - **Accept threshold:** `{RECOGNITION_THRESHOLD}`
                - **Runner-up margin:** `{RECOGNITION_MARGIN}`

                A face is accepted only when the best student is above the threshold and,
                when multiple students are registered, the best match beats the runner-up
                by at least the configured margin. Tune `RECOGNITION_THRESHOLD` and
                `RECOGNITION_MARGIN` in `.env` after collecting real classroom/campus samples.
                """
            )
    
    def _show_debug_analysis(self, image):
        """Show debug analysis of the image"""
        with st.expander("🔍 Image Analysis", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Image Properties:**")
                st.write(f"Shape: {image.shape}")
                st.write(f"Data type: {image.dtype}")
                st.write(f"Value range: [{image.min()}, {image.max()}]")
                
                # Show the image
                st.image(image, caption="Input Image", width=200)
            
            with col2:
                st.markdown("**Quality Analysis:**")
                
                # Brightness analysis
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
                brightness = np.mean(gray)
                
                if brightness < 80:
                    st.error(f"❌ Too dark: {brightness:.1f}")
                elif brightness > 200:
                    st.error(f"❌ Too bright: {brightness:.1f}")
                else:
                    st.success(f"✅ Good brightness: {brightness:.1f}")
                
                # Contrast analysis
                contrast = np.std(gray)
                if contrast < 30:
                    st.error(f"❌ Low contrast: {contrast:.1f}")
                else:
                    st.success(f"✅ Good contrast: {contrast:.1f}")
                
                # Blur analysis
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                if blur_score < 100:
                    st.error(f"❌ Blurry image: {blur_score:.1f}")
                else:
                    st.success(f"✅ Sharp image: {blur_score:.1f}")
        
        # Face detection analysis
        with st.expander("👤 Face Detection Analysis", expanded=True):
            try:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
                
                if len(faces) == 0:
                    st.error("❌ No faces detected")
                    st.info("💡 Try adjusting lighting and face position")
                elif len(faces) > 1:
                    st.warning(f"⚠️ Multiple faces detected: {len(faces)}")
                    st.info("💡 Ensure only one person is visible")
                else:
                    st.success("✅ Single face detected")
                    x, y, w, h = faces[0]
                    st.write(f"Face region: {w}x{h} pixels")
                    
                    # Show face region
                    face_region = image[y:y+h, x:x+w]
                    st.image(face_region, caption="Detected Face", width=150)
                    
            except Exception as e:
                st.error(f"Face detection error: {e}")
        
        # Student comparison analysis
        with st.expander("👥 Student Comparison", expanded=True):
            try:
                self._show_student_comparison_analysis(image)
            except Exception as e:
                st.error(f"Student comparison error: {e}")
    
    def _show_student_comparison_analysis(self, image):
        """Show analysis of comparison with registered students"""
        try:
            # Get all students
            from database.student_repository import StudentRepository
            student_repo = StudentRepository()
            student_embeddings = student_repo.get_student_embeddings()
            
            if not student_embeddings:
                st.error("❌ No students registered in the system")
                st.info("💡 Register students first in Student Management")
                return
            
            st.success(f"✅ Found {len(student_embeddings)} registered students")
            
            # Try to generate embedding for input image
            from face_recognition.recognition_engine import FaceRecognitionEngine
            face_engine = FaceRecognitionEngine()
            
            input_embedding = face_engine.generate_embedding(image, debug_mode=True)
            
            if input_embedding is None:
                st.error("❌ Could not generate embedding for input image")
                return
            
            st.success("✅ Generated embedding for input image")
            
            # Per-template scores, then aggregate max per student (matches live recognition)
            by_student = defaultdict(list)
            for student_id, name, roll_number, known_embedding in student_embeddings:
                try:
                    similarity = face_engine.cosine_similarity(input_embedding, known_embedding)
                    by_student[student_id].append((name, roll_number, similarity))
                except Exception as e:
                    by_student[student_id].append((name, roll_number, 0.0))
                    logger.warning("Similarity error: %s", e)

            student_best = []
            for sid, rows in by_student.items():
                name, roll = rows[0][0], rows[0][1]
                best_s = max(r[2] for r in rows)
                student_best.append({"student_id": sid, "name": name, "roll_number": roll, "similarity": best_s})

            student_best.sort(key=lambda x: x["similarity"], reverse=True)

            st.caption(
                f"Decision uses max similarity per student, threshold ≥ {RECOGNITION_THRESHOLD}, "
                f"and margin ≥ {RECOGNITION_MARGIN} between best and second student."
            )

            st.markdown("**Top students (by best template match):**")
            for i, match in enumerate(student_best[:5], 1):
                similarity = match["similarity"]
                name = match["name"]
                roll = match["roll_number"]
                if similarity >= RECOGNITION_THRESHOLD:
                    st.success(f"{i}. {name} ({roll}): {similarity:.3f} ✅ (above threshold)")
                elif similarity >= RECOGNITION_THRESHOLD * 0.8:
                    st.warning(f"{i}. {name} ({roll}): {similarity:.3f} ⚠️")
                else:
                    st.error(f"{i}. {name} ({roll}): {similarity:.3f} ❌")

            best_match = student_best[0] if student_best else None
            second_sim = student_best[1]["similarity"] if len(student_best) > 1 else 0.0
            if best_match:
                margin_ok = (best_match["similarity"] - second_sim) >= RECOGNITION_MARGIN
                if len(student_best) > 1:
                    st.info(
                        f"Best vs runner-up margin: {best_match['similarity'] - second_sim:.3f} "
                        f"(need ≥ {RECOGNITION_MARGIN}) — {'OK' if margin_ok else 'too close'}"
                    )
                if best_match["similarity"] >= RECOGNITION_THRESHOLD and (
                    len(student_best) == 1 or margin_ok
                ):
                    st.success("🎯 Would accept this image with current settings.")
                elif best_match["similarity"] < RECOGNITION_THRESHOLD:
                    st.warning(
                        f"🎯 Best student below threshold ({RECOGNITION_THRESHOLD}). "
                        "Improve lighting or alignment."
                    )
                else:
                    st.warning("🎯 Ambiguous: top two students too close in similarity.")
                
        except Exception as e:
            st.error(f"Comparison analysis error: {e}")
    
    def _show_manual_entry_form(self):
        """Show manual attendance entry form"""
        st.markdown("### 📝 Manual Attendance Entry")
        
        try:
            from database.student_repository import StudentRepository
            student_repo = StudentRepository()
            students = student_repo.get_all_students()
            
            if not students:
                st.error("❌ No students registered!")
                return
            
            student_options = {f"{s['name']} ({s['roll_number']}) - {s['course']}": s['id'] 
                             for s in students}
            
            with st.form("manual_attendance_form"):
                selected_student = st.selectbox(
                    "👤 Select Student:",
                    options=list(student_options.keys())
                )
                
                if st.form_submit_button("✅ Mark Present", use_container_width=True):
                    if selected_student:
                        student_id = student_options[selected_student]
                        self._mark_manual_attendance(student_id, "present")
        
        except Exception as e:
            st.error(f"Manual entry error: {e}")
    
    def _mark_manual_attendance(self, student_id: int, status: str):
        """Mark attendance manually"""
        try:
            success, message = self.attendance_service.mark_attendance_manual(
                student_id, status, marked_by="manual_entry"
            )
            
            if success:
                st.success(f"✅ {message}")
                st.balloons()
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"❌ {message}")
                
        except Exception as e:
            st.error(f"Error marking manual attendance: {e}")
    
    def _show_student_daily_status(self, student_id: int):
        """Show student's daily attendance status"""
        try:
            # Get today's records for this student
            today_records = self.attendance_service.get_attendance_records(
                start_date=date.today(),
                end_date=date.today(),
                student_id=student_id
            )
            
            if today_records:
                record = today_records[0]  # Should only be one record per day per student
                
                st.markdown("#### 📊 Today's Status")
                status_col1, status_col2 = st.columns(2)
                
                with status_col1:
                    in_time = record.get('time_in', 'Not marked')
                    if in_time and in_time != 'Not marked':
                        # Format time nicely
                        try:
                            if isinstance(in_time, str):
                                time_obj = datetime.fromisoformat(in_time)
                                formatted_time = time_obj.strftime('%I:%M:%S %p')
                            else:
                                formatted_time = in_time.strftime('%I:%M:%S %p')
                            st.metric("🟢 Entry Time", formatted_time)
                        except:
                            st.metric("🟢 Entry Time", str(in_time))
                    else:
                        st.metric("🟢 Entry Time", "Not marked")
                
                with status_col2:
                    out_time = record.get('time_out', 'Not marked')
                    if out_time and out_time != 'Not marked':
                        try:
                            if isinstance(out_time, str):
                                time_obj = datetime.fromisoformat(out_time)
                                formatted_time = time_obj.strftime('%I:%M:%S %p')
                            else:
                                formatted_time = out_time.strftime('%I:%M:%S %p')
                            st.metric("🔴 Exit Time", formatted_time)
                        except:
                            st.metric("🔴 Exit Time", str(out_time))
                    else:
                        st.metric("🔴 Exit Time", "Not marked")
                        
        except Exception as e:
            logger.error(f"Error showing daily status: {e}")
            st.warning("Could not load daily status")
