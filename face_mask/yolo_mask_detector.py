"""
YOLO-World (Ultralytics) open-vocabulary mask detection — no custom training.

Uses pretrained yolov8s-worldv2.pt (auto-downloaded) with text prompts for
"with mask" vs "without mask". Requires CLIP from Ultralytics:

    pip install "git+https://github.com/ultralytics/CLIP.git"

If YOLO or CLIP is unavailable, callers should fall back to RealtimeMaskDetector.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_YOLO_MODEL = None
_YOLO_INIT_ERROR: Optional[str] = None
_YOLO_LOCK = threading.Lock()

# Class indices after set_classes: 0 = mask, 1 = no mask
_CLASS_MASK = 0
_CLASS_NO_MASK = 1


def _get_yolo_world():
    """Lazy-load YOLO-World once; thread-safe."""
    global _YOLO_MODEL, _YOLO_INIT_ERROR

    if _YOLO_INIT_ERROR is not None and _YOLO_MODEL is None:
        return None

    with _YOLO_LOCK:
        if _YOLO_MODEL is not None:
            return _YOLO_MODEL
        try:
            from ultralytics import YOLO

            from config.settings import (
                MASK_YOLO_DEVICE,
                MASK_YOLO_MODEL,
                YOLO_CLASS_MASK_TEXT,
                YOLO_CLASS_NOMASK_TEXT,
            )

            model = YOLO(MASK_YOLO_MODEL)
            model.set_classes([YOLO_CLASS_MASK_TEXT, YOLO_CLASS_NOMASK_TEXT])
            _YOLO_MODEL = model
            _YOLO_INIT_ERROR = None
            logger.info("YOLO-World mask model loaded: %s", MASK_YOLO_MODEL)
            return _YOLO_MODEL
        except Exception as e:
            _YOLO_INIT_ERROR = str(e)
            logger.warning("YOLO-World mask model not available: %s", e)
            return None


def is_yolo_mask_available() -> bool:
    return _get_yolo_world() is not None


def classify_image_yolo(
    image_bgr: np.ndarray,
    conf_min: Optional[float] = None,
) -> Tuple[str, float, Dict[str, Any]]:
    """
    Returns (label, confidence, details) with label in MASK | NO MASK | UNCERTAIN.
    """
    from config.settings import (
        MASK_YOLO_CONF_MASK,
        MASK_YOLO_CONF_NOMASK,
        MASK_YOLO_DEVICE,
    )

    model = _get_yolo_world()
    if model is None:
        return "UNCERTAIN", 0.0, {"error": "yolo_unavailable", "reason": _YOLO_INIT_ERROR}

    if image_bgr is None or image_bgr.size == 0:
        return "UNCERTAIN", 0.0, {"error": "empty_image"}

    cmin = conf_min if conf_min is not None else min(MASK_YOLO_CONF_MASK, MASK_YOLO_CONF_NOMASK) * 0.5

    with _YOLO_LOCK:
        results = model.predict(
            image_bgr,
            conf=cmin,
            device=MASK_YOLO_DEVICE,
            verbose=False,
            imgsz=640,
        )

    r0 = results[0]
    boxes = r0.boxes
    if boxes is None or len(boxes) == 0:
        return "UNCERTAIN", 0.0, {"num_boxes": 0, "yolo": True}

    cls_ids = boxes.cls.cpu().numpy().astype(int)
    confs = boxes.conf.cpu().numpy()

    mask_scores = confs[cls_ids == _CLASS_MASK]
    nomask_scores = confs[cls_ids == _CLASS_NO_MASK]

    best_m = float(mask_scores.max()) if len(mask_scores) else 0.0
    best_nm = float(nomask_scores.max()) if len(nomask_scores) else 0.0

    dbg: Dict[str, Any] = {
        "yolo": True,
        "best_mask": round(best_m, 3),
        "best_no_mask": round(best_nm, 3),
        "num_boxes": int(len(boxes)),
    }

    # Prefer MASK when both fire (safety for attendance)
    if best_m >= MASK_YOLO_CONF_MASK and best_m >= best_nm - 0.05:
        return "MASK", best_m, dbg

    if best_nm >= MASK_YOLO_CONF_NOMASK and best_nm > best_m + 0.05:
        return "NO MASK", best_nm, dbg

    if best_m > 0.15 and best_m > best_nm:
        return "MASK", best_m, dbg

    if best_nm > 0.2:
        return "NO MASK", best_nm, dbg

    return "UNCERTAIN", max(best_m, best_nm), dbg


def annotate_frame_yolo(image_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Run inference and return annotated BGR frame (for WebRTC)."""
    model = _get_yolo_world()
    if model is None:
        raise RuntimeError(_YOLO_INIT_ERROR or "YOLO not loaded")

    from config.settings import MASK_YOLO_DEVICE

    with _YOLO_LOCK:
        results = model.predict(
            image_bgr,
            conf=0.15,
            device=MASK_YOLO_DEVICE,
            verbose=False,
            imgsz=640,
        )

    plotted = results[0].plot()
    if plotted is None:
        return image_bgr.copy(), {}
    if plotted.shape[:2] != image_bgr.shape[:2]:
        import cv2

        plotted = cv2.resize(plotted, (image_bgr.shape[1], image_bgr.shape[0]))
    return plotted, {"ok": True}
