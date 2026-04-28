"""Focus and energy analysis for webcam snapshots and live frames."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

import cv2
import numpy as np

from config.settings import (
    FOCUS_ALERT_THRESHOLD,
    FOCUS_MAX_BLUR_ALERT,
    FOCUS_MIN_FACE_RATIO,
    FOCUS_WARNING_THRESHOLD,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FocusAlert:
    level: str
    message: str


class FocusEnergyService:
    """Heuristic focus / energy detector used for webcam alerts."""

    def __init__(self) -> None:
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
        )

    def analyze_image(self, image_bgr: np.ndarray) -> Dict[str, Any]:
        """Return a score, status, and alerts for a single frame."""
        if image_bgr is None or not isinstance(image_bgr, np.ndarray) or image_bgr.size == 0:
            return self._empty_result("Invalid image supplied.")

        if len(image_bgr.shape) == 2:
            image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
        elif len(image_bgr.shape) == 3 and image_bgr.shape[2] == 4:
            image_bgr = cv2.cvtColor(image_bgr, cv2.COLOR_RGBA2BGR)

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        image_h, image_w = gray.shape[:2]

        brightness = float(np.mean(gray))
        clarity = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        faces = self._detect_faces(gray)

        if len(faces) == 0:
            return {
                "focus_score": 0.0,
                "status": "critical",
                "energy_score": 0.0,
                "alerts": [
                    "No face detected. Center your face in the frame and face the camera.",
                ],
                "face_detected": False,
                "face_box": None,
                "face_ratio": 0.0,
                "eye_count": 0,
                "brightness": round(brightness, 1),
                "clarity": round(clarity, 1),
                "components": {
                    "brightness": self._brightness_component(brightness),
                    "clarity": self._clarity_component(clarity),
                    "centering": 0.0,
                    "eyes": 0.0,
                    "face_size": 0.0,
                },
            }

        face = self._largest_face(faces)
        x, y, w, h = face
        face_ratio = float((w * h) / max(image_w * image_h, 1))
        eye_count = int(self._detect_eyes(gray[y : y + h, x : x + w]))

        centering_component = self._centering_component((x, y, w, h), (image_h, image_w))
        brightness_component = self._brightness_component(brightness)
        clarity_component = self._clarity_component(clarity)
        eye_component = min(1.0, eye_count / 2.0)
        face_size_component = self._face_size_component(face_ratio)

        focus_score = round(
            (
                eye_component * 0.30
                + centering_component * 0.25
                + clarity_component * 0.20
                + brightness_component * 0.15
                + face_size_component * 0.10
            )
            * 100,
            1,
        )

        alerts = self._build_alerts(
            focus_score=focus_score,
            brightness=brightness,
            clarity=clarity,
            face_ratio=face_ratio,
            eye_count=eye_count,
            centering_component=centering_component,
        )

        if focus_score >= FOCUS_WARNING_THRESHOLD:
            status = "focused"
        elif focus_score >= FOCUS_ALERT_THRESHOLD:
            status = "attention"
        else:
            status = "critical"

        return {
            "focus_score": focus_score,
            "energy_score": focus_score,
            "status": status,
            "alerts": alerts,
            "face_detected": True,
            "face_box": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
            "face_ratio": round(face_ratio * 100, 1),
            "eye_count": eye_count,
            "brightness": round(brightness, 1),
            "clarity": round(clarity, 1),
            "components": {
                "brightness": round(brightness_component * 100, 1),
                "clarity": round(clarity_component * 100, 1),
                "centering": round(centering_component * 100, 1),
                "eyes": round(eye_component * 100, 1),
                "face_size": round(face_size_component * 100, 1),
            },
        }

    def annotate_frame(self, image_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Annotate a frame with the current focus analysis."""
        analysis = self.analyze_image(image_bgr)
        output = image_bgr.copy()

        if analysis.get("face_box"):
            box = analysis["face_box"]
            color = self._status_color(analysis["status"])
            cv2.rectangle(
                output,
                (box["x"], box["y"]),
                (box["x"] + box["w"], box["y"] + box["h"]),
                color,
                2,
            )

        self._draw_overlay(output, analysis)
        return output, analysis

    def _empty_result(self, message: str) -> Dict[str, Any]:
        return {
            "focus_score": 0.0,
            "energy_score": 0.0,
            "status": "critical",
            "alerts": [message],
            "face_detected": False,
            "face_box": None,
            "face_ratio": 0.0,
            "eye_count": 0,
            "brightness": 0.0,
            "clarity": 0.0,
            "components": {
                "brightness": 0.0,
                "clarity": 0.0,
                "centering": 0.0,
                "eyes": 0.0,
                "face_size": 0.0,
            },
        }

    def _detect_faces(self, gray: np.ndarray) -> Sequence[Tuple[int, int, int, int]]:
        if self.face_cascade.empty():
            logger.warning("Face cascade not available for focus monitoring")
            return []
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        return faces if len(faces) > 0 else []

    def _detect_eyes(self, face_gray: np.ndarray) -> int:
        if self.eye_cascade.empty() or face_gray.size == 0:
            return 0
        eyes = self.eye_cascade.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20))
        return len(eyes) if eyes is not None else 0

    def _largest_face(self, faces: Sequence[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
        return max(faces, key=lambda box: box[2] * box[3])

    def _centering_component(self, face_box: Tuple[int, int, int, int], image_shape: Tuple[int, int]) -> float:
        image_h, image_w = image_shape
        x, y, w, h = face_box
        face_center_x = x + (w / 2.0)
        face_center_y = y + (h / 2.0)
        frame_center_x = image_w / 2.0
        frame_center_y = image_h / 2.0
        distance = np.hypot(face_center_x - frame_center_x, face_center_y - frame_center_y)
        max_distance = np.hypot(frame_center_x, frame_center_y)
        return float(max(0.0, 1.0 - min(distance / max(max_distance, 1.0), 1.0)))

    def _brightness_component(self, brightness: float) -> float:
        distance = abs(brightness - 140.0)
        return float(max(0.0, 1.0 - min(distance / 140.0, 1.0)))

    def _clarity_component(self, clarity: float) -> float:
        if clarity >= FOCUS_MAX_BLUR_ALERT:
            return 1.0
        return float(max(0.0, min(clarity / max(FOCUS_MAX_BLUR_ALERT, 1.0), 1.0)))

    def _face_size_component(self, face_ratio: float) -> float:
        ideal = 0.18
        distance = abs(face_ratio - ideal)
        return float(max(0.0, 1.0 - min(distance / ideal, 1.0)))

    def _build_alerts(
        self,
        *,
        focus_score: float,
        brightness: float,
        clarity: float,
        face_ratio: float,
        eye_count: int,
        centering_component: float,
    ) -> List[str]:
        alerts: List[str] = []

        if focus_score < FOCUS_ALERT_THRESHOLD:
            alerts.append("Low focus detected. Ask the user to look at the camera.")

        if eye_count == 0:
            alerts.append("Eyes are not clearly visible. Keep the face fully in view.")
        elif eye_count == 1:
            alerts.append("Only one eye is visible. Turn slightly toward the camera.")

        if face_ratio < FOCUS_MIN_FACE_RATIO:
            alerts.append("Move closer to the camera so the face is easier to read.")

        if centering_component < 0.55:
            alerts.append("Center the face inside the frame for a better reading.")

        if brightness < 85:
            alerts.append("Lighting is too dark. Brighten the scene.")
        elif brightness > 205:
            alerts.append("Lighting is too bright. Reduce glare or move away from direct light.")

        if clarity < FOCUS_MAX_BLUR_ALERT:
            alerts.append("Image is blurry. Hold still for a sharper capture.")

        if not alerts:
            alerts.append("Focus looks good.")

        return alerts

    def _status_color(self, status: str) -> Tuple[int, int, int]:
        return {
            "focused": (46, 204, 113),
            "attention": (0, 191, 255),
            "critical": (54, 54, 255),
        }.get(status, (255, 255, 255))

    def _draw_overlay(self, image: np.ndarray, analysis: Dict[str, Any]) -> None:
        overlay = image.copy()
        cv2.rectangle(overlay, (10, 10), (330, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, image, 0.55, 0, image)

        color = self._status_color(analysis.get("status", "critical"))
        cv2.putText(image, f"Focus score: {analysis.get('focus_score', 0):.1f}", (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(image, f"Status: {analysis.get('status', 'critical').title()}", (20, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        alerts = analysis.get("alerts", [])[:2]
        for idx, alert in enumerate(alerts, start=0):
            cv2.putText(image, alert[:42], (20, 102 + idx * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)