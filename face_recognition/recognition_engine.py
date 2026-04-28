"""
Face recognition processing engine - Windows-safe version.

This implementation keeps the existing embedding-based pipeline intact while
removing the hard dependency on DeepFace/TensorFlow/native dlib builds.
It uses OpenCV face detection and a deterministic frequency-domain descriptor.
"""
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from config.settings import EMBEDDING_SIZE, RECOGNITION_MARGIN, RECOGNITION_THRESHOLD
from face_recognition.image_utils import detect_face_in_image, resize_embedding_to_512, validate_image_quality

logger = logging.getLogger(__name__)


class FaceRecognitionEngine:
    """Face recognition engine backed by OpenCV preprocessing."""

    def __init__(self):
        self.embedding_size = EMBEDDING_SIZE
        self.recognition_threshold = RECOGNITION_THRESHOLD
        self.recognition_margin = RECOGNITION_MARGIN
        self._initialize_models()

    def _initialize_models(self):
        """Initialize the recognition pipeline."""
        try:
            logger.info("Initializing face recognition models...")
            test_image = np.ones((224, 224, 3), dtype=np.uint8) * 128
            self._generate_embedding_from_face(test_image)
            logger.info("Face recognition models initialized successfully")
        except Exception as exc:
            logger.warning(f"Model initialization warning: {exc}")

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

    def _generate_embedding_from_face(self, face_image) -> Optional[np.ndarray]:
        """Create a deterministic 512-d descriptor from a detected face crop."""
        try:
            if face_image is None:
                return None

            if len(face_image.shape) == 3:
                gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_image.copy()

            gray = cv2.equalizeHist(cv2.resize(gray, (32, 32)))
            gray = gray.astype(np.float32) / 255.0

            dct = cv2.dct(gray)
            feature_block = dct[:14, :32].flatten()

            # Blend in simple texture statistics to improve separation between faces.
            hist = cv2.calcHist([gray], [0], None, [64], [0.0, 1.0]).flatten().astype(np.float32)
            hist = hist / (np.linalg.norm(hist) + 1e-8)

            embedding = np.concatenate([feature_block, hist], axis=0)
            embedding = resize_embedding_to_512(embedding)

            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding.astype(np.float32)

        except Exception as exc:
            logger.debug(f"Embedding generation error: {exc}")
            return None

    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compare two embeddings and return raw cosine similarity in the [-1, 1] range."""
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
