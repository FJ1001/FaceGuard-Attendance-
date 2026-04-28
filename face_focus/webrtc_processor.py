"""WebRTC processor for live focus and energy alerts."""

from __future__ import annotations

import logging
from collections import deque
from typing import Deque, Dict, List

import av
import numpy as np
from streamlit_webrtc import VideoProcessorBase

from config.settings import FOCUS_ALERT_THRESHOLD, FOCUS_AVERAGE_WINDOW, FOCUS_WARNING_THRESHOLD
from face_focus.focus_energy_service import FocusEnergyService

logger = logging.getLogger(__name__)


class FocusEnergyVideoProcessor(VideoProcessorBase):
    """Annotates webcam frames with a focus score and short alert text."""

    def __init__(self, frame_skip: int = 2, average_window: int = FOCUS_AVERAGE_WINDOW) -> None:
        super().__init__()
        self._service = FocusEnergyService()
        self._frame_skip = max(1, frame_skip)
        self._average_window = max(1, average_window)
        self._idx = 0
        self._last: np.ndarray | None = None
        self._score_history: Deque[float] = deque(maxlen=self._average_window)
        self.latest_analysis: dict = {}

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        self._idx += 1

        if self._idx % self._frame_skip == 0:
            try:
                self._last, analysis = self._service.annotate_frame(img)
                self.latest_analysis = self._record_analysis(analysis)
            except Exception as exc:
                logger.warning("Focus frame processing failed: %s", exc)
                self._last = img
                self.latest_analysis = {
                    "focus_score": 0.0,
                    "rolling_focus_score": 0.0,
                    "status": "critical",
                    "rolling_status": "critical",
                    "alerts": ["Focus analysis temporarily unavailable."],
                    "rolling_alerts": ["Focus analysis temporarily unavailable."],
                }
        elif self._last is None:
            self._last = img

        out = self._last if self._last is not None else img
        return av.VideoFrame.from_ndarray(out, format="bgr24")

    def _record_analysis(self, analysis: Dict) -> Dict:
        """Store the latest focus score and derive rolling average statistics."""
        focus_score = float(analysis.get("focus_score", 0.0))
        self._score_history.append(focus_score)

        rolling_focus_score = round(sum(self._score_history) / max(len(self._score_history), 1), 1)
        rolling_status = self._classify_score(rolling_focus_score)
        rolling_alerts = self._build_rolling_alerts(
            rolling_focus_score=rolling_focus_score,
            sample_count=len(self._score_history),
        )

        enriched = dict(analysis)
        enriched.update(
            {
                "focus_score": focus_score,
                "rolling_focus_score": rolling_focus_score,
                "rolling_status": rolling_status,
                "rolling_alerts": rolling_alerts,
                "average_window": self._average_window,
                "sample_count": len(self._score_history),
            }
        )
        return enriched

    def _classify_score(self, score: float) -> str:
        if score >= FOCUS_WARNING_THRESHOLD:
            return "focused"
        if score >= FOCUS_ALERT_THRESHOLD:
            return "attention"
        return "critical"

    def _build_rolling_alerts(self, *, rolling_focus_score: float, sample_count: int) -> List[str]:
        if sample_count < min(5, self._average_window):
            return [f"Collecting live stats ({sample_count}/{self._average_window})."]

        if rolling_focus_score < FOCUS_ALERT_THRESHOLD:
            return [
                f"Average focus is low at {rolling_focus_score:.1f}/100 over the last {sample_count} frames.",
                "Ask the user to center their face, improve lighting, or hold still.",
            ]

        if rolling_focus_score < FOCUS_WARNING_THRESHOLD:
            return [
                f"Average focus is moderate at {rolling_focus_score:.1f}/100 over the last {sample_count} frames.",
                "Keep tracking the live average before taking action.",
            ]

        return [
            f"Average focus is strong at {rolling_focus_score:.1f}/100 over the last {sample_count} frames.",
        ]