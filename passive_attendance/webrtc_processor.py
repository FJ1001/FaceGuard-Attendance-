"""WebRTC processor for passive classroom attendance."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

import av
import cv2
import numpy as np
from streamlit_webrtc import VideoProcessorBase

from config.settings import (
    PASSIVE_ATTENDANCE_COOLDOWN_SECONDS,
    PASSIVE_CONF_THRESHOLD,
    PASSIVE_CONSECUTIVE_FRAMES,
    PASSIVE_FRAME_SKIP,
    PASSIVE_MIN_VISIBLE_SECONDS,
    PASSIVE_ROLLING_WINDOW,
    PASSIVE_TRACK_DISTANCE_PX,
    PASSIVE_TRACK_MAX_MISSED,
)
from services.passive_attendance_service import PassiveAttendanceService
from services.student_service import StudentService

logger = logging.getLogger(__name__)


@dataclass
class TrackState:
    track_id: str
    centroid: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    first_seen: float
    last_seen: float
    missed: int = 0
    consecutive_hits: int = 0
    recognized_student_id: Optional[int] = None
    recognized_name: str = "Unknown"
    best_confidence: float = 0.0
    rolling_conf: Deque[float] = field(default_factory=lambda: deque(maxlen=PASSIVE_ROLLING_WINDOW))
    attendance_marked: bool = False

    @property
    def visible_sec(self) -> float:
        return max(self.last_seen - self.first_seen, 0.0)


class PassiveAttendanceVideoProcessor(VideoProcessorBase):
    """Detect, track, and recognize multiple faces to auto-mark attendance."""

    def __init__(self, session_id: int, roster_ids: List[int]) -> None:
        super().__init__()
        self.session_id = session_id
        self.roster_ids = set(int(v) for v in roster_ids)
        self.student_service = StudentService()
        self.passive_service = PassiveAttendanceService()
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

        self._frame_idx = 0
        self._tracks: Dict[str, TrackState] = {}
        self._next_track = 1
        self._attendance_cooldown: Dict[int, float] = {}
        self.latest_snapshot: Dict[str, object] = {
            "recognized_count": 0,
            "unknown_count": 0,
            "detected_count": 0,
            "present_marked": 0,
            "tracks": [],
        }

        # Embeddings cache: (student_id, name, roll_number, embedding)
        self._student_embeddings = self.student_service.student_repo.get_student_embeddings()

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        image = frame.to_ndarray(format="bgr24")
        self._frame_idx += 1

        if self._frame_idx % max(PASSIVE_FRAME_SKIP, 1) == 0:
            try:
                annotated = self._process_frame(image)
                return av.VideoFrame.from_ndarray(annotated, format="bgr24")
            except Exception as exc:
                logger.error("Passive attendance frame processing failed: %s", exc)
                return av.VideoFrame.from_ndarray(image, format="bgr24")

        return av.VideoFrame.from_ndarray(image, format="bgr24")

    def _process_frame(self, image: np.ndarray) -> np.ndarray:
        now = time.time()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detections = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))

        dets = []
        for (x, y, w, h) in detections:
            dets.append((int(x), int(y), int(w), int(h), (int(x + w / 2), int(y + h / 2))))

        self._match_tracks(dets, now)
        self._run_recognition(image, now)
        self._cleanup_missed_tracks()

        annotated = image.copy()
        recognized = 0
        unknown = 0
        tracks_payload = []

        for track in self._tracks.values():
            x, y, w, h = track.bbox
            conf = (sum(track.rolling_conf) / len(track.rolling_conf)) if track.rolling_conf else 0.0
            label = f"{track.recognized_name} ({conf:.2f})"
            color = (0, 200, 0) if track.recognized_student_id else (0, 140, 255)
            if track.recognized_student_id:
                recognized += 1
            else:
                unknown += 1

            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            cv2.putText(annotated, label, (x, max(y - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            tracks_payload.append(
                {
                    "track_id": track.track_id,
                    "student_id": track.recognized_student_id,
                    "name": track.recognized_name,
                    "confidence": round(conf, 3),
                    "visible_sec": round(track.visible_sec, 2),
                    "consecutive_hits": track.consecutive_hits,
                    "attendance_marked": track.attendance_marked,
                }
            )

        present_marked = len([t for t in self._tracks.values() if t.attendance_marked])
        self.latest_snapshot = {
            "recognized_count": recognized,
            "unknown_count": unknown,
            "detected_count": len(dets),
            "present_marked": present_marked,
            "tracks": tracks_payload,
            "roster_total": len(self.roster_ids),
        }

        self.passive_service.log_frame_stats(
            session_id=self.session_id,
            detected_count=len(dets),
            recognized_count=recognized,
            unknown_count=unknown,
        )

        return annotated

    def _match_tracks(self, detections: List[Tuple[int, int, int, int, Tuple[int, int]]], now: float) -> None:
        unmatched_track_ids = set(self._tracks.keys())

        for (x, y, w, h, centroid) in detections:
            matched_track = None
            best_dist = 1e9

            for track_id in list(unmatched_track_ids):
                track = self._tracks[track_id]
                dist = ((track.centroid[0] - centroid[0]) ** 2 + (track.centroid[1] - centroid[1]) ** 2) ** 0.5
                if dist < PASSIVE_TRACK_DISTANCE_PX and dist < best_dist:
                    best_dist = dist
                    matched_track = track

            if matched_track:
                matched_track.centroid = centroid
                matched_track.bbox = (x, y, w, h)
                matched_track.last_seen = now
                matched_track.missed = 0
                unmatched_track_ids.discard(matched_track.track_id)
            else:
                track_id = f"T{self._next_track}"
                self._next_track += 1
                self._tracks[track_id] = TrackState(
                    track_id=track_id,
                    centroid=centroid,
                    bbox=(x, y, w, h),
                    first_seen=now,
                    last_seen=now,
                )

        for track_id in unmatched_track_ids:
            self._tracks[track_id].missed += 1

    def _run_recognition(self, image: np.ndarray, now: float) -> None:
        for track in self._tracks.values():
            if track.missed > 0:
                continue

            x, y, w, h = track.bbox
            face_crop = image[max(y, 0):max(y + h, 0), max(x, 0):max(x + w, 0)]
            if face_crop.size == 0:
                continue

            recognized, info, confidence = self._recognize_crop(face_crop)
            track.rolling_conf.append(float(confidence))
            smooth_conf = (sum(track.rolling_conf) / len(track.rolling_conf)) if track.rolling_conf else 0.0

            if recognized and info:
                sid = int(info["student_id"])
                if sid in self.roster_ids:
                    if track.recognized_student_id == sid:
                        track.consecutive_hits += 1
                    else:
                        track.consecutive_hits = 1

                    track.recognized_student_id = sid
                    track.recognized_name = info.get("name", f"Student {sid}")
                    track.best_confidence = max(track.best_confidence, smooth_conf)

                    should_mark, reason = self.passive_service.should_mark_attendance(
                        session_id=self.session_id,
                        student_id=sid,
                        confidence=smooth_conf,
                        visible_sec=track.visible_sec,
                        consecutive_hits=track.consecutive_hits,
                        min_confidence=PASSIVE_CONF_THRESHOLD,
                        min_visible_sec=PASSIVE_MIN_VISIBLE_SECONDS,
                        min_consecutive_frames=PASSIVE_CONSECUTIVE_FRAMES,
                    )

                    cooldown_ok = self._cooldown_ok(sid, now)
                    if should_mark and cooldown_ok and not track.attendance_marked:
                        ok, msg = self.passive_service.mark_attendance(student_id=sid, marked_by="passive_ai")
                        if ok:
                            track.attendance_marked = True
                            self._attendance_cooldown[sid] = now
                            self.passive_service.log_event(
                                session_id=self.session_id,
                                event_type="attendance_marked",
                                student_id=sid,
                                track_id=track.track_id,
                                confidence=smooth_conf,
                                details={"message": msg},
                            )

                    self.passive_service.upsert_presence_log(
                        session_id=self.session_id,
                        student_id=sid,
                        track_id=track.track_id,
                        visible_sec=track.visible_sec,
                        confidence=smooth_conf,
                        marked=track.attendance_marked,
                    )
                else:
                    track.recognized_student_id = None
                    track.recognized_name = "Not in roster"
            else:
                track.recognized_student_id = None
                track.recognized_name = "Unknown"
                if track.visible_sec >= PASSIVE_MIN_VISIBLE_SECONDS:
                    self.passive_service.log_event(
                        session_id=self.session_id,
                        event_type="unknown_face",
                        student_id=None,
                        track_id=track.track_id,
                        confidence=smooth_conf,
                        details={"visible_sec": round(track.visible_sec, 2)},
                    )

    def _recognize_crop(self, face_crop: np.ndarray) -> Tuple[bool, Optional[Dict[str, object]], float]:
        embedding = self.student_service.face_engine.generate_embedding(face_crop)
        if embedding is None or not self._student_embeddings:
            return False, None, 0.0

        best = (None, 0.0, "", "")
        for sid, name, roll, known in self._student_embeddings:
            score = float(self.student_service.face_engine.compare_faces(embedding, known))
            if score > best[1]:
                best = (sid, score, name, roll)

        sid, score, name, roll = best
        if sid is None or score < PASSIVE_CONF_THRESHOLD:
            return False, None, score

        return True, {"student_id": sid, "name": name, "roll_number": roll}, score

    def _cooldown_ok(self, student_id: int, now: float) -> bool:
        last = self._attendance_cooldown.get(student_id)
        if last is None:
            return True
        return (now - last) >= float(PASSIVE_ATTENDANCE_COOLDOWN_SECONDS)

    def _cleanup_missed_tracks(self) -> None:
        to_delete = []
        for track in self._tracks.values():
            if track.missed > PASSIVE_TRACK_MAX_MISSED:
                if track.recognized_student_id is not None:
                    self.passive_service.mark_exit(
                        session_id=self.session_id,
                        student_id=int(track.recognized_student_id),
                    )
                to_delete.append(track.track_id)

        for track_id in to_delete:
            self._tracks.pop(track_id, None)
