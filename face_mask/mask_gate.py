"""
Attendance gate: block marking when a face covering is detected or uncertain.

The attendance path uses the fast OpenCV heuristic detector so Streamlit does
not stall while loading or running heavyweight YOLO inference. The live
WebRTC preview can still use YOLO separately.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

import numpy as np

from config.settings import (
    ATTENDANCE_MASK_CHECK_ENABLED,
    MASK_ATTENDANCE_BLOCK_CONFIDENCE,
    MASK_BLOCK_UNCERTAIN,
)
from face_mask.mask_detector_rt import RealtimeMaskDetector

logger = logging.getLogger(__name__)


def _classify_with_fallback(image_bgr: np.ndarray) -> Tuple[str, float, Dict[str, Any]]:
    """Fast heuristic detector used for attendance gating."""
    details: Dict[str, Any] = {}

    det = RealtimeMaskDetector(strict_attendance=True)
    label, conf, dbg = det.classify_image_best_face(image_bgr)
    details["backend"] = "heuristic"
    details["scores"] = dbg
    return label, conf, details


def _classify_permissive(image_bgr: np.ndarray) -> Tuple[str, float, Dict[str, Any]]:
    """Second-pass heuristic that is less likely to false-positive on uncovered faces."""
    det = RealtimeMaskDetector(strict_attendance=False)
    label, conf, dbg = det.classify_image_best_face(image_bgr)
    return label, conf, {"backend": "heuristic_permissive", "scores": dbg}


def check_face_uncovered_for_attendance(
    image_bgr: np.ndarray,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Returns (allowed_to_mark_attendance, message, details).

    When `MASK_BLOCK_UNCERTAIN` is True (default), UNCERTAIN also blocks
    attendance so users must show a clearly uncovered face.
    """
    if not ATTENDANCE_MASK_CHECK_ENABLED:
        return True, "Mask check disabled.", {"skipped": True}

    if image_bgr is None or not isinstance(image_bgr, np.ndarray) or image_bgr.size == 0:
        return False, "Invalid image. Please capture or upload again.", {}

    label, conf, details = _classify_with_fallback(image_bgr)
    details["label"] = label

    permissive_label, permissive_conf, permissive_details = _classify_permissive(image_bgr)
    details["permissive_label"] = permissive_label
    details["permissive_confidence"] = permissive_conf
    details["permissive_scores"] = permissive_details.get("scores", {})

    if details.get("backend") == "yolo_world" and details.get("num_boxes") == 0:
        return (
            False,
            "Could not clearly see your face in this photo. Face the camera, use good lighting, and try again.",
            details,
        )

    if details.get("backend") == "heuristic" and details.get("scores", {}).get("error") == "no_face":
        return (
            False,
            "No face detected. Center your face in the frame, use good lighting, and try again.",
            details,
        )

    strong_mask_confident = (
        label == "MASK"
        and conf >= MASK_ATTENDANCE_BLOCK_CONFIDENCE
        and permissive_label == "MASK"
        and permissive_conf >= max(0.55, MASK_ATTENDANCE_BLOCK_CONFIDENCE - 0.15)
    )

    if strong_mask_confident:
        return (
            False,
            "Face mask detected. Please remove your mask so your face is visible, then take the photo again.",
            details,
        )

    if label == "MASK":
        return (
            True,
            "Possible face covering detected, but confidence was too low to block attendance. Please retake the photo if this looks wrong.",
            details,
        )

    if label == "UNCERTAIN":
        if MASK_BLOCK_UNCERTAIN:
            return (
                False,
                "Could not confirm your face is uncovered. Remove any mask, use bright lighting, face the camera, and try again.",
                details,
            )
        return True, "Proceeding with uncertain mask check (configured to allow).", details

    if label == "NO MASK":
        return (
            True,
            "Face covering check passed.",
            details,
        )

    return False, "Could not verify face. Please try again with a clear frontal photo.", details
