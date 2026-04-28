"""
Enhanced face recognition engine with improved discriminative features.

This version uses multiple feature extractors to create more discriminative
embeddings that can better distinguish between different faces.
"""
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from config.settings import EMBEDDING_SIZE, RECOGNITION_MARGIN, RECOGNITION_THRESHOLD
from face_recognition.image_utils import detect_face_in_image, resize_embedding_to_512, validate_image_quality

logger = logging.getLogger(__name__)


class EnhancedFaceRecognitionEngine:
    """
    Improved face recognition engine using multiple feature extractors:
    - LBP (Local Binary Patterns) for texture
    - Gabor filters for edge/orientation
    - HOG (Histogram of Oriented Gradients) for structure
    - Enhanced DCT for frequency features
    """

    def __init__(self):
        self.embedding_size = EMBEDDING_SIZE
        self.recognition_threshold = RECOGNITION_THRESHOLD
        self.recognition_margin = RECOGNITION_MARGIN
        self._initialize_models()

    def _initialize_models(self):
        """Initialize the recognition pipeline."""
        try:
            logger.info("Initializing enhanced face recognition models...")
            # Test with sample image
            test_image = np.ones((224, 224, 3), dtype=np.uint8) * 128
            self._generate_embedding_from_face(test_image)
            logger.info("Enhanced face recognition models initialized successfully")
        except Exception as exc:
            logger.warning(f"Model initialization warning: {exc}")

    def _extract_lbp_features(self, gray: np.ndarray, num_points: int = 24, radius: int = 3) -> np.ndarray:
        """Extract Local Binary Pattern features for texture analysis."""
        try:
            # Resize for consistent processing
            resized = cv2.resize(gray, (128, 128))
            
            # Simple LBP implementation
            lbp = np.zeros_like(resized, dtype=np.uint8)
            h, w = resized.shape
            
            for i in range(radius, h - radius):
                for j in range(radius, w - radius):
                    center = resized[i, j]
                    binary = 0
                    binary |= (resized[i-radius, j] >= center) << 0
                    binary |= (resized[i-radius, j+radius] >= center) << 1
                    binary |= (resized[i, j+radius] >= center) << 2
                    binary |= (resized[i+radius, j+radius] >= center) << 3
                    binary |= (resized[i+radius, j] >= center) << 4
                    binary |= (resized[i+radius, j-radius] >= center) << 5
                    binary |= (resized[i, j-radius] >= center) << 6
                    binary |= (resized[i-radius, j-radius] >= center) << 7
                    lbp[i, j] = binary
            
            # Compute histogram
            hist = cv2.calcHist([lbp], [0], None, [256], [0, 256]).flatten()
            hist = hist / (hist.sum() + 1e-8)  # Normalize
            return hist.astype(np.float32)
            
        except Exception as e:
            logger.warning(f"LBP extraction failed: {e}")
            return np.zeros(256, dtype=np.float32)

    def _extract_hog_features(self, gray: np.ndarray, cells_per_block: int = 2, 
                             block_size: int = 16, cell_size: int = 8) -> np.ndarray:
        """Extract Histogram of Oriented Gradients features."""
        try:
            resized = cv2.resize(gray, (128, 128))
            
            # Compute gradients
            gx = cv2.Sobel(resized, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(resized, cv2.CV_32F, 0, 1, ksize=3)
            
            # Magnitude and orientation
            mag, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)
            
            # Quantize orientation into 9 bins (0-180 degrees)
            angle = np.mod(angle, 180)
            bins = np.floor(angle / 20).astype(np.int32)  # 9 bins
            bins = np.clip(bins, 0, 8)
            
            # Compute HOG by accumulating magnitudes into bins
            h, w = mag.shape
            hog = np.zeros(9, dtype=np.float32)
            
            for i in range(h):
                for j in range(w):
                    hog[bins[i, j]] += mag[i, j]
            
            # Normalize
            norm = np.linalg.norm(hog)
            if norm > 0:
                hog = hog / norm
            
            return hog
            
        except Exception as e:
            logger.warning(f"HOG extraction failed: {e}")
            return np.zeros(9, dtype=np.float32)

    def _extract_gabor_features(self, gray: np.ndarray) -> np.ndarray:
        """Extract Gabor filter responses for edge/orientation detection."""
        try:
            resized = cv2.resize(gray, (64, 64))
            
            # Multiple orientations and frequencies
            orientations = [0, 45, 90, 135]
            frequencies = [0.1, 0.3, 0.5]
            
            features = []
            
            for theta in orientations:
                for freq in frequencies:
                    # Create Gabor kernel
                    kernel = cv2.getGaborKernel(
                        (11, 11),  # ksize
                        sigma=4.0,
                        theta=np.radians(theta),
                        lambd=1.0/freq,
                        gamma=0.5,
                        psi=0
                    )
                    
                    # Apply filter
                    filtered = cv2.filter2D(resized, cv2.CV_8UC3, kernel)
                    
                    # Extract statistics
                    features.append(np.mean(filtered))
                    features.append(np.std(filtered))
                    features.append(np.max(filtered))
            
            features = np.array(features, dtype=np.float32)
            
            # Normalize
            norm = np.linalg.norm(features)
            if norm > 0:
                features = features / norm
            
            return features
            
        except Exception as e:
            logger.warning(f"Gabor extraction failed: {e}")
            return np.zeros(len(orientations) * len(frequencies) * 3, dtype=np.float32)

    def _extract_enhanced_dct_features(self, gray: np.ndarray) -> np.ndarray:
        """Enhanced DCT features with better frequency selection."""
        try:
            resized = cv2.equalizeHist(cv2.resize(gray, (64, 64)))
            resized = resized.astype(np.float32) / 255.0
            
            # 2D DCT
            dct = cv2.dct(resized)
            
            # Extract low-frequency components (more discriminative)
            # Take top-left corner but with more coefficients
            low_freq = dct[:16, :16].flatten()
            
            # Also take some mid-frequency components
            mid_freq = dct[16:24, :8].flatten()
            
            combined = np.concatenate([low_freq, mid_freq])
            return combined.astype(np.float32)
            
        except Exception as e:
            logger.warning(f"Enhanced DCT extraction failed: {e}")
            return np.zeros(320, dtype=np.float32)

    def _generate_embedding_from_face(self, face_image) -> Optional[np.ndarray]:
        """Create a discriminative multi-feature embedding from a detected face crop."""
        try:
            if face_image is None:
                return None

            # Convert to grayscale
            if len(face_image.shape) == 3:
                gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_image.copy()

            # Extract multiple feature types
            lbp_features = self._extract_lbp_features(gray)  # 256 dims
            hog_features = self._extract_hog_features(gray)   # 9 dims
            gabor_features = self._extract_gabor_features(gray)  # 36 dims
            dct_features = self._extract_enhanced_dct_features(gray)  # 320 dims

            # Combine all features
            embedding = np.concatenate([
                lbp_features,
                hog_features,
                gabor_features,
                dct_features
            ])

            # Resize to exactly 512 dimensions
            embedding = resize_embedding_to_512(embedding)

            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding.astype(np.float32)

        except Exception as exc:
            logger.debug(f"Embedding generation error: {exc}")
            return None

    def generate_embedding(self, image, debug_mode: bool = False) -> Optional[np.ndarray]:
        """Generate a 512-d face embedding from an input image."""
        try:
            if image is None:
                logger.error("Input image is None")
                return None

            if len(image.shape) != 3:
                logger.error(f"Invalid image shape: {image.shape}")
                return None

            is_valid, message = validate_image_quality(image)
            if not is_valid:
                logger.warning(f"Image quality validation failed: {message}")
                if debug_mode:
                    return None

            ok, detect_message, face_image = detect_face_in_image(image)
            if not ok or face_image is None:
                logger.warning(f"Face detection failed: {detect_message}")
                return None

            embedding = self._generate_embedding_from_face(face_image)
            if embedding is None:
                logger.error("Failed to generate embedding from detected face")
                return None

            return embedding

        except Exception as exc:
            logger.error(f"Error generating embedding: {exc}")
            if debug_mode:
                import traceback
                logger.error(traceback.format_exc())
            return None

    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compare two embeddings and return cosine similarity in the [-1, 1] range."""
        try:
            if embedding1 is None or embedding2 is None:
                return 0.0

            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = float(np.dot(embedding1, embedding2) / (norm1 * norm2))
            return max(-1.0, min(1.0, similarity))

        except Exception as exc:
            logger.error(f"Error comparing faces: {exc}")
            return 0.0

    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Backward-compatible cosine similarity helper used by the UI."""
        return self.compare_faces(embedding1, embedding2)

    def euclidean_distance(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Backward-compatible Euclidean distance helper."""
        try:
            if embedding1 is None or embedding2 is None:
                return float("inf")

            return float(np.linalg.norm(embedding1 - embedding2))

        except Exception as exc:
            logger.error(f"Error calculating euclidean distance: {exc}")
            return float("inf")

    def recognize_face(
        self,
        image,
        student_embeddings: List[Tuple],
    ) -> Tuple[bool, Optional[Dict], float, Dict]:
        """Recognize a face against the known student gallery."""
        meta = {
            "reason": "error",
            "best_similarity": 0.0,
            "second_similarity": 0.0,
            "threshold": self.recognition_threshold,
            "required_margin": self.recognition_margin,
        }

        try:
            probe_embedding = self.generate_embedding(image)
            if probe_embedding is None:
                meta["reason"] = "no_face"
                return False, None, 0.0, meta

            best_per_student: Dict[int, Tuple[float, str, str]] = {}
            for student_id, name, roll_number, known_embedding in student_embeddings:
                score = self.compare_faces(probe_embedding, known_embedding)
                current_best = best_per_student.get(student_id)
                if current_best is None or score > current_best[0]:
                    best_per_student[student_id] = (score, name, roll_number)

            if not best_per_student:
                meta["reason"] = "no_gallery"
                return False, None, 0.0, meta

            ranked = sorted(best_per_student.items(), key=lambda item: item[1][0], reverse=True)
            best_student_id, (best_score, best_name, best_roll_number) = ranked[0]
            second_score = ranked[1][1][0] if len(ranked) > 1 else 0.0

            meta["best_similarity"] = float(best_score)
            meta["second_similarity"] = float(second_score)

            if best_score < self.recognition_threshold:
                meta["reason"] = "low_confidence"
                return False, None, float(best_score), meta

            if len(ranked) > 1 and (best_score - second_score) < self.recognition_margin:
                meta["reason"] = "ambiguous"
                return False, None, float(best_score), meta

            meta["reason"] = "matched"
            student_info = {
                "student_id": best_student_id,
                "name": best_name,
                "roll_number": best_roll_number,
            }
            return True, student_info, float(best_score), meta

        except Exception as exc:
            logger.error(f"Error recognizing face: {exc}")
            meta["detail"] = str(exc)
            return False, None, 0.0, meta

    def validate_embedding_quality(self, embedding: np.ndarray) -> Tuple[bool, str]:
        """Validate that an embedding is usable for registration and matching."""
        try:
            if embedding is None:
                return False, "Embedding is None"

            if not isinstance(embedding, np.ndarray):
                return False, "Embedding is not a numpy array"

            if embedding.ndim != 1:
                return False, f"Embedding must be 1-dimensional, got shape {embedding.shape}"

            if embedding.shape[0] != self.embedding_size:
                return False, (
                    f"Embedding size {embedding.shape[0]} != expected {self.embedding_size}"
                )

            if np.isnan(embedding).any():
                return False, "Embedding contains NaN values"

            if np.isinf(embedding).any():
                return False, "Embedding contains infinite values"

            if np.allclose(embedding, 0):
                return False, "Embedding is all zeros"

            norm = np.linalg.norm(embedding)
            if norm < 0.1:
                return False, f"Embedding norm too small: {norm}"

            return True, "Embedding is valid"

        except Exception as exc:
            logger.error(f"Error validating embedding: {exc}")
            return False, f"Validation error: {exc}"

    def batch_generate_embeddings(self, images: List[np.ndarray], debug_mode: bool = False) -> List[Optional[np.ndarray]]:
        """Generate embeddings for a list of images."""
        embeddings: List[Optional[np.ndarray]] = []

        for image in images:
            embeddings.append(self.generate_embedding(image, debug_mode=debug_mode))

        return embeddings
