"""
Image conversion utilities
"""
import numpy as np
import cv2
from PIL import Image
import io
import logging
from typing import Optional, Tuple, Union

logger = logging.getLogger(__name__)

class ImageConverter:
    """Handle image format conversion and validation"""
    
    @staticmethod
    def streamlit_uploaded_to_opencv(uploaded_file) -> Optional[np.ndarray]:
        """Convert Streamlit uploaded file to OpenCV format"""
        try:
            if uploaded_file is None:
                return None
            
            # Read bytes from uploaded file
            file_bytes = uploaded_file.read()
            
            # Convert to numpy array
            nparr = np.frombuffer(file_bytes, np.uint8)
            
            # Decode image
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("Failed to decode uploaded image")
                return None
            
            logger.info(f"Converted uploaded file to OpenCV format: {image.shape}")
            return image
            
        except Exception as e:
            logger.error(f"Error converting uploaded file: {e}")
            return None
    
    @staticmethod
    def streamlit_camera_to_opencv(camera_input) -> Optional[np.ndarray]:
        """Convert Streamlit camera input to OpenCV format"""
        try:
            if camera_input is None:
                return None
            
            # Camera input is already a PIL Image or bytes
            if hasattr(camera_input, 'read'):
                # If it's a file-like object
                bytes_data = camera_input.read()
            else:
                # If it's already bytes
                bytes_data = camera_input.getvalue()
            
            # Convert to PIL Image first
            pil_image = Image.open(io.BytesIO(bytes_data))
            
            # Convert PIL to OpenCV
            opencv_image = ImageConverter.pil_to_opencv(pil_image)
            
            logger.info(f"Converted camera input to OpenCV format: {opencv_image.shape}")
            return opencv_image
            
        except Exception as e:
            logger.error(f"Error converting camera input: {e}")
            return None
    
    @staticmethod
    def pil_to_opencv(pil_image: Image.Image) -> Optional[np.ndarray]:
        """Convert PIL Image to OpenCV format"""
        try:
            # Convert PIL to RGB if not already
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to numpy array
            numpy_array = np.array(pil_image)
            
            # Convert RGB to BGR (OpenCV format)
            opencv_image = cv2.cvtColor(numpy_array, cv2.COLOR_RGB2BGR)
            
            logger.info(f"Converted PIL to OpenCV format: {opencv_image.shape}")
            return opencv_image
            
        except Exception as e:
            logger.error(f"Error converting PIL to OpenCV: {e}")
            return None
    
    @staticmethod
    def validate_opencv_image(image) -> Tuple[bool, str]:
        """Validate OpenCV image format"""
        try:
            if image is None:
                return False, "Image is None"
            
            if not isinstance(image, np.ndarray):
                return False, f"Image is not numpy array, got {type(image)}"
            
            if len(image.shape) not in [2, 3]:
                return False, f"Invalid image dimensions: {image.shape}"
            
            if len(image.shape) == 3 and image.shape[2] not in [1, 3, 4]:
                return False, f"Invalid number of channels: {image.shape[2]}"
            
            if image.size == 0:
                return False, "Empty image"
            
            # Check data type
            if image.dtype not in [np.uint8, np.float32, np.float64]:
                return False, f"Invalid data type: {image.dtype}"
            
            # Check value range
            if image.dtype == np.uint8:
                if image.min() < 0 or image.max() > 255:
                    return False, f"Invalid value range for uint8: [{image.min()}, {image.max()}]"
            
            return True, "Image is valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def ensure_uint8_format(image: np.ndarray) -> Optional[np.ndarray]:
        """Ensure image is in uint8 format"""
        try:
            if image is None:
                return None
            
            if image.dtype == np.uint8:
                return image
            
            # Convert to uint8
            if image.dtype in [np.float32, np.float64]:
                # Assume float images are in range [0, 1]
                if image.max() <= 1.0:
                    image = (image * 255).astype(np.uint8)
                else:
                    image = np.clip(image, 0, 255).astype(np.uint8)
            else:
                image = np.clip(image, 0, 255).astype(np.uint8)
            
            return image
            
        except Exception as e:
            logger.error(f"Error converting to uint8: {e}")
            return None
    
    @staticmethod
    def ensure_3_channel(image: np.ndarray) -> Optional[np.ndarray]:
        """Ensure image has 3 channels (BGR)"""
        try:
            if image is None:
                return None
            
            if len(image.shape) == 2:
                # Grayscale to BGR
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif len(image.shape) == 3:
                if image.shape[2] == 1:
                    # Single channel to BGR
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                elif image.shape[2] == 4:
                    # RGBA to BGR
                    image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
                elif image.shape[2] == 3:
                    # Already 3 channels
                    pass
                else:
                    logger.error(f"Unsupported channel count: {image.shape[2]}")
                    return None
            
            return image
            
        except Exception as e:
            logger.error(f"Error ensuring 3 channels: {e}")
            return None
    
    @staticmethod
    def preprocess_for_face_recognition(image_input) -> Optional[np.ndarray]:
        """Complete preprocessing pipeline for face recognition"""
        try:
            # Step 1: Handle different input types
            if hasattr(image_input, 'read') or hasattr(image_input, 'getvalue'):
                # Streamlit file upload or camera input
                if hasattr(image_input, 'type') and 'image' in image_input.type:
                    # File upload
                    image = ImageConverter.streamlit_uploaded_to_opencv(image_input)
                else:
                    # Camera input
                    image = ImageConverter.streamlit_camera_to_opencv(image_input)
            elif isinstance(image_input, np.ndarray):
                # Already numpy array
                image = image_input.copy()
            else:
                logger.error(f"Unsupported image input type: {type(image_input)}")
                return None
            
            if image is None:
                logger.error("Failed to convert image input")
                return None
            
            # Step 2: Validate image
            is_valid, message = ImageConverter.validate_opencv_image(image)
            if not is_valid:
                logger.error(f"Image validation failed: {message}")
                return None
            
            # Step 3: Ensure proper format
            image = ImageConverter.ensure_uint8_format(image)
            if image is None:
                logger.error("Failed to convert to uint8 format")
                return None
            
            image = ImageConverter.ensure_3_channel(image)
            if image is None:
                logger.error("Failed to ensure 3 channels")
                return None
            
            # Step 4: Final validation
            is_valid, message = ImageConverter.validate_opencv_image(image)
            if not is_valid:
                logger.error(f"Final validation failed: {message}")
                return None
            
            logger.info(f"Successfully preprocessed image: {image.shape}, {image.dtype}")
            return image
            
        except Exception as e:
            logger.error(f"Error in preprocessing pipeline: {e}")
            return None

# Convenience functions
def convert_streamlit_image(image_input) -> Optional[np.ndarray]:
    """Quick function to convert any Streamlit image input"""
    return ImageConverter.preprocess_for_face_recognition(image_input)

def validate_image_for_cv2(image) -> bool:
    """Quick validation for OpenCV operations"""
    is_valid, _ = ImageConverter.validate_opencv_image(image)
    return is_valid
