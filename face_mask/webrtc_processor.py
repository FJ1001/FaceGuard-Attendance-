"""WebRTC video processor: YOLO-World overlay when available, else heuristics."""

from __future__ import annotations

import logging
from typing import Optional

import av
import numpy as np
from streamlit_webrtc import VideoProcessorBase

from config.settings import MASK_USE_YOLO
from face_mask.mask_detector_rt import RealtimeMaskDetector

logger = logging.getLogger(__name__)


class MaskVideoProcessor(VideoProcessorBase):
    """
    Processes incoming webcam frames. Skips some frames for CPU headroom;
    reuses last annotation between processed frames to keep video smooth.
    """

    def __init__(self, frame_skip: int = 2) -> None:
        super().__init__()
        self._detector = RealtimeMaskDetector(strict_attendance=False)
        self._frame_skip = max(1, frame_skip)
        self._idx = 0
        self._last: Optional[np.ndarray] = None

    def _annotate(self, img: np.ndarray) -> np.ndarray:
        if MASK_USE_YOLO:
            try:
                from face_mask.yolo_mask_detector import annotate_frame_yolo, is_yolo_mask_available

                if is_yolo_mask_available():
                    out, _ = annotate_frame_yolo(img)
                    return out
            except Exception as e:
                logger.debug("YOLO WebRTC annotate fallback: %s", e)
        annotated, _ = self._detector.annotate_frame(img)
        return annotated

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        self._idx += 1

        if self._idx % self._frame_skip == 0:
            try:
                self._last = self._annotate(img)
            except Exception as e:
                logger.warning("Mask frame processing failed: %s", e)
                self._last = img
        elif self._last is not None:
            pass
        else:
            self._last = img

        out = self._last if self._last is not None else img
        return av.VideoFrame.from_ndarray(out, format="bgr24")
