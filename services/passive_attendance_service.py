"""Passive AI attendance service with session and roster awareness."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class PassiveAttendanceService:
    """Backend logic for passive classroom attendance automation."""

    def __init__(self) -> None:
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS class_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        class_name TEXT NOT NULL,
                        course TEXT,
                        camera_source TEXT DEFAULT 'webcam',
                        start_time TEXT,
                        end_time TEXT,
                        is_active INTEGER DEFAULT 0,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS class_roster (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER NOT NULL,
                        student_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(session_id, student_id),
                        FOREIGN KEY (session_id) REFERENCES class_sessions(id) ON DELETE CASCADE,
                        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS passive_presence_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER NOT NULL,
                        student_id INTEGER NOT NULL,
                        track_id TEXT,
                        first_seen TEXT,
                        last_seen TEXT,
                        total_visible_sec REAL DEFAULT 0,
                        max_confidence REAL DEFAULT 0,
                        attendance_marked INTEGER DEFAULT 0,
                        entry_count INTEGER DEFAULT 1,
                        exit_count INTEGER DEFAULT 0,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(session_id, student_id),
                        FOREIGN KEY (session_id) REFERENCES class_sessions(id) ON DELETE CASCADE,
                        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS passive_detection_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        event_type TEXT NOT NULL,
                        student_id INTEGER,
                        track_id TEXT,
                        confidence REAL,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS passive_frame_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER NOT NULL,
                        detected_count INTEGER DEFAULT 0,
                        recognized_count INTEGER DEFAULT 0,
                        unknown_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES class_sessions(id) ON DELETE CASCADE
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS class_timetable (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        class_name TEXT NOT NULL,
                        course TEXT,
                        day_of_week INTEGER NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT NOT NULL,
                        is_active INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_class_sessions_active ON class_sessions(is_active)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_presence_session_student ON passive_presence_logs(session_id, student_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_events_session_time ON passive_detection_events(session_id, created_at DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_frame_stats_session_time ON passive_frame_stats(session_id, created_at DESC)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_timetable_day ON class_timetable(day_of_week, start_time, end_time)")
                conn.commit()
        except Exception as exc:
            logger.error("Error ensuring passive attendance schema: %s", exc)

    def create_session(
        self,
        *,
        class_name: str,
        course: str,
        camera_source: str,
        created_by: str,
        start_time: Optional[str] = None,
        student_ids: Optional[List[int]] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE class_sessions SET is_active = 0 WHERE is_active = 1")
                cur.execute(
                    """
                    INSERT INTO class_sessions (class_name, course, camera_source, start_time, is_active, created_by)
                    VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (
                        class_name.strip() or "Active Class",
                        course.strip() if course else "",
                        camera_source or "webcam",
                        start_time or datetime.now().isoformat(timespec="seconds"),
                        created_by or "admin",
                    ),
                )
                session_id = int(cur.lastrowid)

                if student_ids:
                    for student_id in student_ids:
                        cur.execute(
                            "INSERT OR IGNORE INTO class_roster (session_id, student_id) VALUES (?, ?)",
                            (session_id, int(student_id)),
                        )

                conn.commit()
                return True, "Passive session started", session_id
        except Exception as exc:
            logger.error("Error creating passive session: %s", exc)
            return False, str(exc), None

    def list_sessions(self, limit: int = 30) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, class_name, course, camera_source, start_time, end_time, is_active, created_by, created_at
                    FROM class_sessions
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]
        except Exception as exc:
            logger.error("Error listing passive sessions: %s", exc)
            return []

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, class_name, course, camera_source, start_time, end_time, is_active, created_by, created_at
                    FROM class_sessions
                    WHERE is_active = 1
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as exc:
            logger.error("Error getting active passive session: %s", exc)
            return None

    def stop_active_session(self) -> Tuple[bool, str]:
        try:
            now = datetime.now().isoformat(timespec="seconds")
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE class_sessions SET is_active = 0, end_time = ? WHERE is_active = 1",
                    (now,),
                )
                conn.commit()
                return True, "Active passive session stopped"
        except Exception as exc:
            logger.error("Error stopping passive session: %s", exc)
            return False, str(exc)

    def replace_roster(self, session_id: int, student_ids: List[int]) -> Tuple[bool, str]:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM class_roster WHERE session_id = ?", (session_id,))
                for sid in student_ids:
                    cur.execute(
                        "INSERT OR IGNORE INTO class_roster (session_id, student_id) VALUES (?, ?)",
                        (session_id, int(sid)),
                    )
                conn.commit()
                return True, "Roster updated"
        except Exception as exc:
            logger.error("Error replacing roster: %s", exc)
            return False, str(exc)

    def get_roster_student_ids(self, session_id: int) -> Set[int]:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT student_id FROM class_roster WHERE session_id = ?", (session_id,))
                return {int(row["student_id"]) for row in cur.fetchall()}
        except Exception as exc:
            logger.error("Error loading roster ids: %s", exc)
            return set()

    def should_mark_attendance(
        self,
        *,
        session_id: int,
        student_id: int,
        confidence: float,
        visible_sec: float,
        consecutive_hits: int,
        min_confidence: float,
        min_visible_sec: float,
        min_consecutive_frames: int,
    ) -> Tuple[bool, str]:
        roster = self.get_roster_student_ids(session_id)
        if student_id not in roster:
            return False, "student-not-in-roster"
        if confidence < min_confidence:
            return False, "low-confidence"
        if visible_sec < min_visible_sec:
            return False, "insufficient-visibility"
        if consecutive_hits < min_consecutive_frames:
            return False, "insufficient-consecutive-frames"
        if self._is_already_marked(session_id, student_id):
            return False, "already-marked"
        return True, "ok"

    def _is_already_marked(self, session_id: int, student_id: int) -> bool:
        today = datetime.now().date().isoformat()
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id FROM attendance WHERE student_id = ? AND date = ?",
                    (student_id, today),
                )
                if cur.fetchone():
                    return True
                cur.execute(
                    "SELECT attendance_marked FROM passive_presence_logs WHERE session_id = ? AND student_id = ?",
                    (session_id, student_id),
                )
                row = cur.fetchone()
                return bool(row and int(row["attendance_marked"]) == 1)
        except Exception as exc:
            logger.error("Error checking duplicate attendance: %s", exc)
            return False

    def mark_attendance(self, *, student_id: int, marked_by: str = "passive_ai") -> Tuple[bool, str]:
        try:
            now = datetime.now().isoformat(timespec="seconds")
            today = datetime.now().date().isoformat()
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM students WHERE id = ?", (student_id,))
                student = cur.fetchone()
                if not student:
                    return False, "Student not found"

                cur.execute(
                    "SELECT id FROM attendance WHERE student_id = ? AND date = ?",
                    (student_id, today),
                )
                if cur.fetchone():
                    return False, "Attendance already marked"

                cur.execute(
                    """
                    INSERT INTO attendance (student_id, date, time_in, status, marked_by)
                    VALUES (?, ?, ?, 'present', ?)
                    """,
                    (student_id, today, now, marked_by),
                )
                conn.commit()
                return True, f"Attendance marked for {student['name']}"
        except Exception as exc:
            logger.error("Error marking passive attendance: %s", exc)
            return False, str(exc)

    def upsert_presence_log(
        self,
        *,
        session_id: int,
        student_id: int,
        track_id: str,
        visible_sec: float,
        confidence: float,
        marked: bool,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, first_seen, max_confidence, entry_count, exit_count
                    FROM passive_presence_logs
                    WHERE session_id = ? AND student_id = ?
                    """,
                    (session_id, student_id),
                )
                row = cur.fetchone()
                if row:
                    max_conf = max(float(row["max_confidence"] or 0), float(confidence))
                    cur.execute(
                        """
                        UPDATE passive_presence_logs
                        SET last_seen = ?,
                            total_visible_sec = ?,
                            max_confidence = ?,
                            attendance_marked = CASE WHEN ? = 1 THEN 1 ELSE attendance_marked END,
                            track_id = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (now, float(visible_sec), max_conf, 1 if marked else 0, track_id, int(row["id"])),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO passive_presence_logs (
                            session_id, student_id, track_id, first_seen, last_seen,
                            total_visible_sec, max_confidence, attendance_marked
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            student_id,
                            track_id,
                            now,
                            now,
                            float(visible_sec),
                            float(confidence),
                            1 if marked else 0,
                        ),
                    )
                conn.commit()
        except Exception as exc:
            logger.error("Error upserting presence log: %s", exc)

    def mark_exit(self, *, session_id: int, student_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE passive_presence_logs
                    SET exit_count = exit_count + 1,
                        last_seen = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ? AND student_id = ?
                    """,
                    (now, session_id, student_id),
                )
                conn.commit()
        except Exception as exc:
            logger.error("Error marking exit: %s", exc)

    def log_event(
        self,
        *,
        session_id: Optional[int],
        event_type: str,
        student_id: Optional[int] = None,
        track_id: Optional[str] = None,
        confidence: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO passive_detection_events (session_id, event_type, student_id, track_id, confidence, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        event_type,
                        student_id,
                        track_id,
                        confidence,
                        json.dumps(details or {}, default=str),
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.error("Error logging passive event: %s", exc)

    def get_live_dashboard(self, session_id: int) -> Dict[str, Any]:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()

                roster_ids = self.get_roster_student_ids(session_id)
                present_count = 0
                if roster_ids:
                    placeholders = ",".join(["?"] * len(roster_ids))
                    today = datetime.now().date().isoformat()
                    cur.execute(
                        f"SELECT COUNT(DISTINCT student_id) as c FROM attendance WHERE date = ? AND student_id IN ({placeholders})",
                        [today, *list(roster_ids)],
                    )
                    present_count = int(cur.fetchone()["c"])

                cur.execute(
                    """
                    SELECT p.student_id, s.name, s.roll_number, p.first_seen, p.last_seen,
                           p.total_visible_sec, p.max_confidence, p.attendance_marked,
                           p.entry_count, p.exit_count
                    FROM passive_presence_logs p
                    JOIN students s ON s.id = p.student_id
                    WHERE p.session_id = ?
                    ORDER BY p.last_seen DESC
                    """,
                    (session_id,),
                )
                logs = [dict(row) for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT created_at, event_type, student_id, track_id, confidence, details
                    FROM passive_detection_events
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT 20
                    """,
                    (session_id,),
                )
                events = [dict(row) for row in cur.fetchall()]

                total_roster = len(roster_ids)
                absent_count = max(total_roster - present_count, 0)

                occupancy = self.get_occupancy_analytics(session_id=session_id, limit=120)

                return {
                    "session_id": session_id,
                    "roster_total": total_roster,
                    "present_count": present_count,
                    "absent_count": absent_count,
                    "presence_logs": logs,
                    "recent_events": events,
                    "occupancy": occupancy,
                }
        except Exception as exc:
            logger.error("Error loading passive dashboard: %s", exc)
            return {
                "session_id": session_id,
                "roster_total": 0,
                "present_count": 0,
                "absent_count": 0,
                "presence_logs": [],
                "recent_events": [],
                "occupancy": {"latest": {}, "history": []},
            }

    def log_frame_stats(self, *, session_id: int, detected_count: int, recognized_count: int, unknown_count: int) -> None:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO passive_frame_stats (session_id, detected_count, recognized_count, unknown_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, int(detected_count), int(recognized_count), int(unknown_count)),
                )
                conn.commit()
        except Exception as exc:
            logger.error("Error logging frame stats: %s", exc)

    def get_occupancy_analytics(self, *, session_id: int, limit: int = 120) -> Dict[str, Any]:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT detected_count, recognized_count, unknown_count, created_at
                    FROM passive_frame_stats
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (session_id, int(limit)),
                )
                rows = [dict(r) for r in cur.fetchall()]

            history = list(reversed(rows))
            if not history:
                return {
                    "latest": {
                        "detected_count": 0,
                        "recognized_count": 0,
                        "unknown_count": 0,
                        "recognition_rate": 0.0,
                    },
                    "history": [],
                }

            latest = history[-1]
            detected = int(latest.get("detected_count", 0))
            recognized = int(latest.get("recognized_count", 0))
            recognition_rate = (recognized / detected * 100.0) if detected > 0 else 0.0

            return {
                "latest": {
                    "detected_count": detected,
                    "recognized_count": recognized,
                    "unknown_count": int(latest.get("unknown_count", 0)),
                    "recognition_rate": round(recognition_rate, 1),
                },
                "history": history,
            }
        except Exception as exc:
            logger.error("Error loading occupancy analytics: %s", exc)
            return {"latest": {}, "history": []}
