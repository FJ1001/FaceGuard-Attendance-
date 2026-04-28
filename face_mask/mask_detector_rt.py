"""
Face covering detection for still images and video frames.

Uses OpenCV face detection plus YCbCr skin, HSV mask-color cues, texture
(Laplacian), and upper-vs-lower face asymmetry. Biased toward blocking
attendance when a mask is likely (high recall on masks).

Confidence scores are conservative heuristics — not ML probabilities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceMaskResult:
    label: str
    confidence: float
    box: Tuple[int, int, int, int]


class RealtimeMaskDetector:
    """
    Detect faces and classify MASK / NO MASK / UNCERTAIN.

    `strict_attendance=True` uses tighter rules so uncertain cases lean MASK
    (safer for blocking attendance).
    """

    def __init__(self, strict_attendance: bool = False):
        self.strict_attendance = strict_attendance
        self._cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    @staticmethod
    def _roi_lower_face(frame_bgr: np.ndarray, x: int, y: int, w: int, h: int, frac: float) -> np.ndarray:
        """Bottom `frac` of face box (mouth / chin band)."""
        fh = max(8, int(h * frac))
        y0 = y + h - fh
        return frame_bgr[y0 : y + h, x : x + w]

    @staticmethod
    def _roi_mid_face(frame_bgr: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
        """Middle vertical third (nose / upper cheeks)."""
        t = y + int(h * 0.33)
        b = y + int(h * 0.66)
        return frame_bgr[t:b, x : x + w]

    @staticmethod
    def _ycbcr_skin_ratio(bgr: np.ndarray) -> float:
        """Fraction of pixels in common skin ranges (YCbCr, inclusive of darker tones)."""
        if bgr.size == 0 or bgr.shape[0] < 2 or bgr.shape[1] < 2:
            return 0.0
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        cr = ycrcb[:, :, 1].astype(np.int16)
        cb = ycrcb[:, :, 2].astype(np.int16)
        # Wider Cr/Cb envelope for varied lighting and skin tones
        skin = (cr >= 130) & (cr <= 185) & (cb >= 75) & (cb <= 140)
        return float(np.count_nonzero(skin)) / float(skin.size)

    @staticmethod
    def _fabric_like_mask_fraction(bgr: np.ndarray) -> float:
        """
        Fraction of pixels that look like common surgical / cloth mask colors
        (blue, green, white/grey) in the ROI — not skin.
        """
        if bgr.size == 0:
            return 0.0
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        h = hsv[:, :, 0].astype(np.int16)
        s = hsv[:, :, 1].astype(np.int16)
        v = hsv[:, :, 2].astype(np.int16)
        blue = (h >= 85) & (h <= 125) & (s >= 25) & (v >= 35)
        green = (h >= 30) & (h <= 95) & (s >= 20) & (v >= 35)
        white = (s <= 55) & (v >= 130)
        combined = blue | green | white
        return float(np.count_nonzero(combined)) / float(combined.size)

    @staticmethod
    def _laplacian_var(bgr: np.ndarray) -> float:
        if bgr.size == 0:
            return 0.0
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def _classify_face(
        self, frame_bgr: np.ndarray, x: int, y: int, w: int, h: int
    ) -> Tuple[str, float, dict]:
        """
        Returns label, display confidence (capped heuristic), and debug scores.
        """
        mouth = self._roi_lower_face(frame_bgr, x, y, w, h, 0.48)
        mid = self._roi_mid_face(frame_bgr, x, y, w, h)

        sm = self._ycbcr_skin_ratio(mouth)
        s_mid = self._ycbcr_skin_ratio(mid)
        lap_m = self._laplacian_var(mouth)
        fabric = self._fabric_like_mask_fraction(mouth)

        dbg = {
            "mouth_skin": round(sm, 3),
            "mid_skin": round(s_mid, 3),
            "lap_mouth": round(lap_m, 1),
            "fabric_frac": round(fabric, 3),
        }

        strict = self.strict_attendance

        # Strong mask-like fabric colors in mouth/chin area
        if fabric >= (0.22 if strict else 0.28):
            conf = min(0.78, 0.52 + fabric * 0.9)
            return "MASK", conf, dbg

        # Lower face much less "skin" than mid-face → typical with mask / covering
        if s_mid >= 0.16 and sm < s_mid * 0.45 and sm < 0.12:
            conf = min(0.75, 0.55 + (s_mid - sm) * 1.2)
            return "MASK", conf, dbg

        # Very little skin + low texture in mouth band (smooth fabric / occlusion)
        if sm <= (0.08 if strict else 0.10) and lap_m <= (75 if strict else 85):
            conf = min(0.76, 0.58 + (0.12 - sm) * 2.0)
            return "MASK", conf, dbg

        if sm <= (0.10 if strict else 0.12) and lap_m <= (65 if strict else 75):
            return "MASK", min(0.72, 0.54 + (0.15 - sm)), dbg

        # Clear no-covering: enough skin texture in lower face
        if (
            sm >= (0.18 if strict else 0.16)
            and lap_m >= (100 if strict else 90)
            and fabric < (0.15 if strict else 0.18)
            and sm >= s_mid * 0.70
        ):
            # Capped confidence — never claim > ~72% as "probability"
            raw = 0.48 + min(0.24, (sm - 0.18) * 1.5 + (lap_m - 100) * 0.001)
            return "NO MASK", min(0.72, raw), dbg

        # Ambiguous: in strict mode treat as not allowed for attendance
        if strict:
            return "UNCERTAIN", 0.48, dbg

        # Non-strict (live preview): split borderline cases
        if sm >= 0.14 and lap_m >= 80 and fabric < 0.18:
            return "NO MASK", min(0.65, 0.5 + (sm - 0.16)), dbg

        return "UNCERTAIN", 0.45, dbg

    def annotate_frame(self, frame_bgr: np.ndarray) -> Tuple[np.ndarray, List[FaceMaskResult]]:
        """Draw boxes and labels; confidence shown as capped heuristic %."""
        out = frame_bgr.copy()
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=4,
            minSize=(48, 48),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        results: List[FaceMaskResult] = []

        color_map = {
            "MASK": (40, 165, 255),
            "NO MASK": (50, 200, 70),
            "UNCERTAIN": (0, 200, 255),
        }

        for (x, y, w, h) in faces:
            label, conf, _ = self._classify_face(frame_bgr, x, y, w, h)
            color = color_map[label]
            pct = int(round(min(0.72, conf) * 100))
            cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
            text = f"{label} ~{pct}%"
            cv2.putText(
                out,
                text,
                (x, max(y - 8, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                color,
                2,
                cv2.LINE_AA,
            )
            results.append(FaceMaskResult(label=label, confidence=conf, box=(x, y, w, h)))

        return out, results

    def classify_image_best_face(self, frame_bgr: np.ndarray) -> Tuple[str, float, dict]:
        """
        Classify the largest frontal face (for attendance gating).
        Returns label, confidence, debug dict. If no face, returns UNCERTAIN.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.06,
            minNeighbors=3,
            minSize=(40, 40),
        )
        if len(faces) == 0:
            return "UNCERTAIN", 0.0, {"error": "no_face"}

        # Largest box
        faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
        x, y, w, h = faces[0]
        label, conf, dbg = self._classify_face(frame_bgr, x, y, w, h)
        dbg["box"] = (int(x), int(y), int(w), int(h))
        return label, conf, dbg
