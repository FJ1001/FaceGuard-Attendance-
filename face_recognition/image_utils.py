"""
Image processing utilities - Windows-safe version.

DeepFace remains supported when installed, but the default path now falls back
to OpenCV Haar cascades so the app can still work on Windows without TensorFlow
or native build tooling.
"""
import os
import numpy as np
import cv2
import logging
from functools import lru_cache
from typing import Tuple, Optional

from utils.image_converter import ImageConverter, validate_image_for_cv2
from config.settings import DETECTOR_BACKEND

logger = logging.getLogger(__name__)


def _deepface():
    """Import DeepFace lazily when available."""
    try:
        from deepface import DeepFace

        return DeepFace
    except ImportError:
        return None


@lru_cache(maxsize=1)
def _haar_face_cascade():
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    return cascade if not cascade.empty() else None

def ensure_rgb(frame_bgr):
    """Convert BGR to RGB for DeepFace compatibility with proper validation"""
    try:
        # Validate input first
        if not validate_image_for_cv2(frame_bgr):
            logger.error("Invalid image for color conversion")
            return frame_bgr
        
        if len(frame_bgr.shape) == 3 and frame_bgr.shape[2] == 3:
            # Ensure it's uint8
            if frame_bgr.dtype != np.uint8:
                frame_bgr = ImageConverter.ensure_uint8_format(frame_bgr)
            
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            return rgb
        else:
            return frame_bgr
            
    except Exception as e:
        logger.warning(f"Color conversion failed: {e}")
        return frame_bgr

def resize_embedding_to_512(embedding) -> np.ndarray:
    """Ensure embedding is exactly 512 dimensions"""
    from config.settings import EMBEDDING_SIZE
    
    try:
        embedding = np.array(embedding, dtype=np.float32)
        
        if embedding.shape[0] == EMBEDDING_SIZE:
            return embedding
        elif embedding.shape[0] > EMBEDDING_SIZE:
            logger.warning(f"Truncating embedding from {embedding.shape[0]} to {EMBEDDING_SIZE}")
            return embedding[:EMBEDDING_SIZE]
        else:
            logger.warning(f"Padding embedding from {embedding.shape[0]} to {EMBEDDING_SIZE}")
            padded = np.zeros(EMBEDDING_SIZE, dtype=np.float32)
            padded[:len(embedding)] = embedding
            return padded
            
    except Exception as e:
        logger.error(f"Error resizing embedding: {e}")
        return np.zeros(512, dtype=np.float32)

def validate_image_quality(image, min_face_size: int = 50) -> Tuple[bool, str]:
    """Validate image quality for face recognition"""
    try:
        # First validate the image format
        if not validate_image_for_cv2(image):
            return False, "Invalid image format for OpenCV"
        
        height, width = image.shape[:2]
        
        if width < 100 or height < 100:
            return False, "Image resolution too low (minimum 100x100)"
        
        # Convert to grayscale safely
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        mean_brightness = np.mean(gray)
        
        if mean_brightness < 30:
            return False, "Image too dark"
        elif mean_brightness > 225:
            return False, "Image too bright"
        
        # Basic blur detection
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            return False, "Image appears to be blurry"
        
        return True, "Image quality is acceptable"
        
    except Exception as e:
        logger.error(f"Error validating image quality: {e}")
        return False, f"Error validating image: {str(e)}"

def detect_face_in_image(image) -> Tuple[bool, str, Optional[np.ndarray]]:
    """Detect a single face in an image.

    If DeepFace is available, it uses the configured detector backend.
    Otherwise it falls back to OpenCV Haar cascades, which keeps Windows
    installs working without TensorFlow or native build dependencies.
    """
    try:
        if not validate_image_for_cv2(image):
            return False, "Invalid image format", None

        image = ImageConverter.ensure_uint8_format(image)
        image = ImageConverter.ensure_3_channel(image)

        if image is None:
            return False, "Failed to preprocess image", None

        deepface = _deepface()
        if deepface is not None:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            faces = deepface.extract_faces(
                img_path=rgb,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=False,
            )

            if faces:
                if len(faces) > 1:
                    return False, "Multiple faces detected. Please ensure only one face is visible", None

                face_obj = faces[0]
                face_img = face_obj.get("face", None)
                if face_img is not None:
                    face_bgr = cv2.cvtColor((face_img * 255).astype("uint8"), cv2.COLOR_RGB2BGR)
                    face_resized = cv2.resize(face_bgr, (224, 224))
                    return True, "Face detected successfully", face_resized

        # OpenCV fallback for Windows or any environment without DeepFace
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        cascade = _haar_face_cascade()
        if cascade is None:
            return False, "OpenCV face detector unavailable", None

        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces) == 0:
            return False, "No face detected in image", None
        if len(faces) > 1:
            return False, "Multiple faces detected. Please ensure only one face is visible", None

        x, y, w, h = faces[0]
        face = image[y:y + h, x:x + w]
        if face.size == 0:
            return False, "Failed to crop face region", None

        face_resized = cv2.resize(face, (224, 224))
        return True, "Face detected successfully", face_resized

    except Exception as e:
        logger.error(f"Error detecting face: {e}")
        return False, f"Face detection error: {str(e)}", None

def enhance_image_for_recognition(image) -> np.ndarray:
    """Enhance image quality for better face recognition"""
    try:
        # Validate image first
        if not validate_image_for_cv2(image):
            logger.warning("Cannot enhance invalid image")
            return image
        
        # Convert to grayscale for processing
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Convert back to BGR if original was color
        if len(image.shape) == 3:
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        # Apply slight Gaussian blur to reduce noise
        enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        return enhanced
        
    except Exception as e:
        logger.error(f"Error enhancing image: {e}")
        return image

def preprocess_image_for_embedding(image) -> np.ndarray:
    """Preprocess image specifically for embedding generation"""
    try:
        # Validate and fix image format first
        if not validate_image_for_cv2(image):
            logger.error("Cannot preprocess invalid image")
            return image
        
        # Ensure RGB format
        rgb_image = ensure_rgb(image)
        
        # Enhance image quality
        enhanced = enhance_image_for_recognition(rgb_image)
        
        # Normalize pixel values
        if enhanced.dtype == np.uint8:
            normalized = enhanced.astype(np.float32) / 255.0
        else:
            normalized = enhanced.astype(np.float32)
        
        return normalized
        
    except Exception as e:
        logger.error(f"Error preprocessing image: {e}")
        return image.astype(np.float32) / 255.0 if image is not None else np.zeros((224, 224, 3), dtype=np.float32)


def count_faces_in_image(image) -> int:
    """Return the number of faces detected in an image using Haar cascade.

    Used for proxy/impersonation detection — if more than one face is found,
    the attendance submission should be flagged as suspicious.
    Returns 0 if detection fails.
    """
    try:
        if not validate_image_for_cv2(image):
            return 0

        img = ImageConverter.ensure_uint8_format(image)
        if img is None:
            return 0

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        gray = cv2.equalizeHist(gray)
        cascade = _haar_face_cascade()
        if cascade is None:
            return 0

        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(50, 50))
        return int(len(faces))

    except Exception as e:
        logger.warning(f"count_faces_in_image error: {e}")
        return 0

