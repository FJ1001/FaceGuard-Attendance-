"""
Attendance debugging component
Debug tools for face recognition during attendance marking
"""
import streamlit as st
import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from face_recognition.recognition_engine import FaceRecognitionEngine
from services.student_service import StudentService
from services.attendance_service import AttendanceService

class AttendanceDebugger:
    """Debug component for attendance recognition issues"""
    
    def __init__(self):
        self.face_engine = FaceRecognitionEngine()
        self.student_service = StudentService()
        self.attendance_service = AttendanceService()
    
    def debug_recognition_failure(self, image) -> Dict:
        """Debug why face recognition failed"""
        debug_info = {
            'image_analysis': {},
            'face_detection': {},
            'embedding_generation': {},
            'student_comparison': {},
            'recommendations': []
        }
        
        try:
            # 1. Analyze input image
            debug_info['image_analysis'] = self._analyze_input_image(image)
            
            # 2. Test face detection
            debug_info['face_detection'] = self._test_face_detection(image)
            
            # 3. Test embedding generation
            debug_info['embedding_generation'] = self._test_embedding_generation(image)
            
            # 4. Compare with registered students
            debug_info['student_comparison'] = self._test_student_comparison(image)
            
            # 5. Generate recommendations
            debug_info['recommendations'] = self._generate_recommendations(debug_info)
            
        except Exception as e:
            debug_info['error'] = str(e)
        
        return debug_info
    
    def _analyze_input_image(self, image) -> Dict:
        """Analyze the input image quality"""
        try:
            analysis = {
                'shape': image.shape if image is not None else None,
                'dtype': str(image.dtype) if image is not None else None,
                'brightness': None,
                'contrast': None,
                'blur_score': None
            }
            
            if image is not None:
                # Convert to grayscale for analysis
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                
                # Brightness analysis
                analysis['brightness'] = np.mean(gray)
                
                # Contrast analysis
                analysis['contrast'] = np.std(gray)
                
                # Blur detection using Laplacian variance
                analysis['blur_score'] = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _test_face_detection(self, image) -> Dict:
        """Test face detection with multiple methods"""
        detection_results = {
            'opencv_detection': False,
            'deepface_detection': False,
            'face_count': 0,
            'face_regions': []
        }
        
        try:
            # Test OpenCV face detection
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
            
            detection_results['opencv_detection'] = len(faces) > 0
            detection_results['face_count'] = len(faces)
            detection_results['face_regions'] = faces.tolist() if len(faces) > 0 else []
            
            # Test DeepFace detection
            try:
                from deepface import DeepFace
                result = DeepFace.extract_faces(image, enforce_detection=True, detector_backend='opencv')
                detection_results['deepface_detection'] = len(result) > 0
            except:
                detection_results['deepface_detection'] = False
            
        except Exception as e:
            detection_results['error'] = str(e)
        
        return detection_results
    
    def _test_embedding_generation(self, image) -> Dict:
        """Test embedding generation with different approaches"""
        embedding_results = {
            'standard_approach': False,
            'skip_detection_approach': False,
            'opencv_crop_approach': False,
            'embedding_quality': None,
            'best_embedding': None
        }
        
        try:
            # Test standard approach
            embedding = self.face_engine.generate_embedding(image, debug_mode=True)
            if embedding is not None:
                embedding_results['standard_approach'] = True
                embedding_results['best_embedding'] = embedding
                is_valid, msg = self.face_engine.validate_embedding_quality(embedding)
                embedding_results['embedding_quality'] = {'valid': is_valid, 'message': msg}
            
            # If standard failed, try other approaches
            if not embedding_results['standard_approach']:
                # Try skip detection
                try:
                    from deepface import DeepFace
                    result = DeepFace.represent(
                        img_path=image,
                        model_name='ArcFace',
                        detector_backend='skip',
                        enforce_detection=False
                    )
                    if result:
                        embedding_results['skip_detection_approach'] = True
                except:
                    pass
                
                # Try with OpenCV face crop
                try:
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                    
                    if len(faces) > 0:
                        x, y, w, h = faces[0]
                        face_crop = image[y:y+h, x:x+w]
                        crop_embedding = self.face_engine.generate_embedding(face_crop, debug_mode=True)
                        if crop_embedding is not None:
                            embedding_results['opencv_crop_approach'] = True
                            if embedding_results['best_embedding'] is None:
                                embedding_results['best_embedding'] = crop_embedding
                except:
                    pass
        
        except Exception as e:
            embedding_results['error'] = str(e)
        
        return embedding_results
    
    def _test_student_comparison(self, image) -> Dict:
        """Test comparison with all registered students"""
        comparison_results = {
            'total_students': 0,
            'comparisons_made': 0,
            'best_match': None,
            'all_similarities': [],
            'threshold_used': self.face_engine.recognition_threshold
        }
        
        try:
            # Get all student embeddings
            from database.student_repository import StudentRepository
            student_repo = StudentRepository()
            student_embeddings = student_repo.get_student_embeddings()
            
            comparison_results['total_students'] = len(student_embeddings)
            
            if len(student_embeddings) == 0:
                comparison_results['error'] = "No students registered in the system"
                return comparison_results
            
            # Generate embedding for input image
            input_embedding = self.face_engine.generate_embedding(image, debug_mode=True)
            
            if input_embedding is None:
                comparison_results['error'] = "Could not generate embedding for input image"
                return comparison_results
            
            # Compare with all students
            similarities = []
            
            for student_id, name, roll_number, known_embedding in student_embeddings:
                try:
                    similarity = self.face_engine.cosine_similarity(input_embedding, known_embedding)
                    similarities.append({
                        'student_id': student_id,
                        'name': name,
                        'roll_number': roll_number,
                        'similarity': similarity
                    })
                    comparison_results['comparisons_made'] += 1
                except Exception as e:
                    similarities.append({
                        'student_id': student_id,
                        'name': name,
                        'roll_number': roll_number,
                        'similarity': 0.0,
                        'error': str(e)
                    })
            
            # Sort by similarity
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            comparison_results['all_similarities'] = similarities
            
            if similarities:
                comparison_results['best_match'] = similarities[0]
            
        except Exception as e:
            comparison_results['error'] = str(e)
        
        return comparison_results
    
    def _generate_recommendations(self, debug_info: Dict) -> List[str]:
        """Generate recommendations based on debug analysis"""
        recommendations = []
        
        try:
            # Image quality recommendations
            image_analysis = debug_info.get('image_analysis', {})
            if image_analysis:
                brightness = image_analysis.get('brightness', 128)
                contrast = image_analysis.get('contrast', 50)
                blur_score = image_analysis.get('blur_score', 500)
                
                if brightness < 80:
                    recommendations.append("📸 Image is too dark - use better lighting")
                elif brightness > 200:
                    recommendations.append("📸 Image is too bright - reduce lighting or move away from light source")
                
                if contrast < 30:
                    recommendations.append("📊 Low contrast - ensure good lighting contrast between face and background")
                
                if blur_score < 100:
                    recommendations.append("🌀 Image appears blurry - use a sharper, more focused image")
            
            # Face detection recommendations
            face_detection = debug_info.get('face_detection', {})
            if face_detection:
                if not face_detection.get('opencv_detection', False):
                    recommendations.append("👤 Face not detected - ensure face is clearly visible and facing camera")
                
                face_count = face_detection.get('face_count', 0)
                if face_count > 1:
                    recommendations.append("👥 Multiple faces detected - ensure only one person is in the image")
                elif face_count == 0:
                    recommendations.append("❌ No face detected - check image quality and face visibility")
            
            # Student comparison recommendations
            student_comparison = debug_info.get('student_comparison', {})
            if student_comparison:
                total_students = student_comparison.get('total_students', 0)
                
                if total_students == 0:
                    recommendations.append("📝 No students registered - register students first before marking attendance")
                else:
                    best_match = student_comparison.get('best_match')
                    if best_match:
                        similarity = best_match.get('similarity', 0)
                        threshold = student_comparison.get('threshold_used', 0.6)
                        
                        if similarity < threshold:
                            recommendations.append(f"🎯 Best match similarity ({similarity:.3f}) below threshold ({threshold})")
                            recommendations.append("💡 Try using photos more similar to registration images")
                            
                            if similarity > (threshold - 0.2):
                                recommendations.append("⚙️ Consider temporarily lowering recognition threshold")
            
            # General recommendations
            if len(recommendations) == 0:
                recommendations.append("🔄 Try taking a new photo with better lighting and angle")
                recommendations.append("👨‍🎓 Ensure the person is registered in the system")
                recommendations.append("📐 Use similar angle and distance as registration photos")
        
        except Exception as e:
            recommendations.append(f"❌ Error generating recommendations: {str(e)}")
        
        return recommendations
    
    def render_debug_panel(self, image) -> Dict:
        """Render complete debug panel for attendance recognition"""
        st.markdown("### 🔍 Face Recognition Debug Panel")
        
        with st.spinner("🔍 Analyzing recognition failure..."):
            debug_info = self.debug_recognition_failure(image)
        
        # Display results in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Image Analysis", "👤 Face Detection", "🧠 Embedding", "👥 Student Match"])
        
        with tab1:
            self._render_image_analysis_tab(debug_info.get('image_analysis', {}))
        
        with tab2:
            self._render_face_detection_tab(debug_info.get('face_detection', {}))
        
        with tab3:
            self._render_embedding_tab(debug_info.get('embedding_generation', {}))
        
        with tab4:
            self._render_student_comparison_tab(debug_info.get('student_comparison', {}))
        
        # Show recommendations
        st.markdown("### 💡 Recommendations")
        recommendations = debug_info.get('recommendations', [])
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                st.info(f"{i}. {rec}")
        else:
            st.success("✅ No specific issues detected - try the general troubleshooting steps")
        
        return debug_info
    
    def _render_image_analysis_tab(self, analysis: Dict):
        """Render image analysis tab"""
        if 'error' in analysis:
            st.error(f"❌ Analysis error: {analysis['error']}")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Image Shape", str(analysis.get('shape', 'Unknown')))
            st.metric("Data Type", analysis.get('dtype', 'Unknown'))
        
        with col2:
            brightness = analysis.get('brightness', 0)
            st.metric("Brightness", f"{brightness:.1f}", 
                     delta="Good" if 80 <= brightness <= 200 else "Poor")
            
            contrast = analysis.get('contrast', 0)
            st.metric("Contrast", f"{contrast:.1f}",
                     delta="Good" if contrast >= 30 else "Low")
            
            blur_score = analysis.get('blur_score', 0)
            st.metric("Sharpness", f"{blur_score:.1f}",
                     delta="Sharp" if blur_score >= 100 else "Blurry")
    
    def _render_face_detection_tab(self, detection: Dict):
        """Render face detection tab"""
        if 'error' in detection:
            st.error(f"❌ Detection error: {detection['error']}")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            opencv_status = "✅ Detected" if detection.get('opencv_detection') else "❌ Not Detected"
            st.metric("OpenCV Detection", opencv_status)
            
            face_count = detection.get('face_count', 0)
            st.metric("Faces Found", face_count)
        
        with col2:
            deepface_status = "✅ Detected" if detection.get('deepface_detection') else "❌ Not Detected"
            st.metric("DeepFace Detection", deepface_status)
            
            if detection.get('face_regions'):
                st.json({"Face Regions": detection['face_regions']})
    
    def _render_embedding_tab(self, embedding: Dict):
        """Render embedding generation tab"""
        if 'error' in embedding:
            st.error(f"❌ Embedding error: {embedding['error']}")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Generation Methods:**")
            if embedding.get('standard_approach'):
                st.success("✅ Standard approach")
            else:
                st.error("❌ Standard approach")
            
            if embedding.get('skip_detection_approach'):
                st.success("✅ Skip detection approach")
            else:
                st.error("❌ Skip detection approach")
        
        with col2:
            st.write("**Alternative Methods:**")
            if embedding.get('opencv_crop_approach'):
                st.success("✅ OpenCV crop approach")
            else:
                st.error("❌ OpenCV crop approach")
            
            quality = embedding.get('embedding_quality')
            if quality:
                if quality.get('valid'):
                    st.success(f"✅ Quality: {quality.get('message')}")
                else:
                    st.error(f"❌ Quality: {quality.get('message')}")
    
    def _render_student_comparison_tab(self, comparison: Dict):
        """Render student comparison tab"""
        if 'error' in comparison:
            st.error(f"❌ Comparison error: {comparison['error']}")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Students", comparison.get('total_students', 0))
            st.metric("Comparisons Made", comparison.get('comparisons_made', 0))
            st.metric("Recognition Threshold", f"{comparison.get('threshold_used', 0.6):.3f}")
        
        with col2:
            best_match = comparison.get('best_match')
            if best_match:
                st.write("**Best Match:**")
                st.write(f"👤 Name: {best_match.get('name')}")
                st.write(f"🎫 Roll: {best_match.get('roll_number')}")
                st.write(f"📊 Similarity: {best_match.get('similarity', 0):.3f}")
                
                # Show if it would pass with lower threshold
                similarity = best_match.get('similarity', 0)
                if similarity >= 0.4:
                    st.info(f"💡 Would match with threshold ≤ {similarity:.3f}")
        
        # Show all similarities
        similarities = comparison.get('all_similarities', [])
        if similarities:
            st.markdown("**All Student Similarities:**")
            
            similarity_data = []
            for sim in similarities[:10]:  # Show top 10
                similarity_data.append({
                    'Name': sim.get('name'),
                    'Roll': sim.get('roll_number'),
                    'Similarity': f"{sim.get('similarity', 0):.3f}",
                    'Status': '✅ Match' if sim.get('similarity', 0) >= comparison.get('threshold_used', 0.6) else '❌ No Match'
                })
            
            if similarity_data:
                st.dataframe(similarity_data, use_container_width=True, hide_index=True)

# Global instance
attendance_debugger = AttendanceDebugger()
