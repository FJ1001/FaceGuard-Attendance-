"""Persistence and analytics for live focus monitoring sessions."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class FocusSessionService:
    """Store and query focus monitoring sessions per student."""

    def __init__(self) -> None:
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS focus_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        session_started_at TEXT,
                        session_ended_at TEXT,
                        sample_count INTEGER DEFAULT 0,
                        avg_focus_score REAL DEFAULT 0,
                        avg_rolling_score REAL DEFAULT 0,
                        min_focus_score REAL DEFAULT 0,
                        max_focus_score REAL DEFAULT 0,
                        final_status TEXT,
                        alerts_count INTEGER DEFAULT 0,
                        details_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_focus_sessions_student_date ON focus_sessions(student_id, created_at DESC)"
                )
                conn.commit()
        except Exception as exc:
            logger.error("Error ensuring focus session table: %s", exc)

    def save_session_report(self, student_id: int, summary: Dict[str, Any], frames: List[Dict[str, Any]]) -> bool:
        """Save one completed focus session report."""
        try:
            if not student_id or not frames:
                return False

            started = frames[0].get("captured_at")
            ended = frames[-1].get("captured_at")
            details_json = json.dumps({"summary": summary, "frames": frames}, default=str)

            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO focus_sessions (
                        student_id,
                        session_started_at,
                        session_ended_at,
                        sample_count,
                        avg_focus_score,
                        avg_rolling_score,
                        min_focus_score,
                        max_focus_score,
                        final_status,
                        alerts_count,
                        details_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        started,
                        ended,
                        int(summary.get("sample_count", 0)),
                        float(summary.get("avg_focus_score", 0.0)),
                        float(summary.get("avg_rolling_score", 0.0)),
                        float(summary.get("min_focus_score", 0.0)),
                        float(summary.get("max_focus_score", 0.0)),
                        summary.get("final_status", "unknown"),
                        int(summary.get("alerts_count", 0)),
                        details_json,
                    ),
                )
                conn.commit()
                return True
        except Exception as exc:
            logger.error("Error saving focus session: %s", exc)
            return False

    def get_student_focus_sessions(self, student_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent focus sessions for one student."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, student_id, session_started_at, session_ended_at,
                           sample_count, avg_focus_score, avg_rolling_score,
                           min_focus_score, max_focus_score, final_status,
                           alerts_count, created_at
                    FROM focus_sessions
                    WHERE student_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (student_id, limit),
                )
                rows = cursor.fetchall()
                return [
                    {
                        "id": row["id"],
                        "student_id": row["student_id"],
                        "session_started_at": row["session_started_at"],
                        "session_ended_at": row["session_ended_at"],
                        "sample_count": row["sample_count"],
                        "avg_focus_score": row["avg_focus_score"],
                        "avg_rolling_score": row["avg_rolling_score"],
                        "min_focus_score": row["min_focus_score"],
                        "max_focus_score": row["max_focus_score"],
                        "final_status": row["final_status"],
                        "alerts_count": row["alerts_count"],
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]
        except Exception as exc:
            logger.error("Error loading student focus sessions: %s", exc)
            return []

    def get_student_focus_analytics(self, student_id: int) -> Dict[str, Any]:
        """Aggregate analytics for one student's saved focus sessions."""
        sessions = self.get_student_focus_sessions(student_id=student_id, limit=200)
        if not sessions:
            return {
                "total_sessions": 0,
                "avg_focus_score": 0.0,
                "avg_rolling_score": 0.0,
                "total_alerts": 0,
                "last_status": "n/a",
                "status_breakdown": {},
                "risk_band": "n/a",
                "risk_reason": "No sessions captured yet.",
                "trend": "n/a",
            }

        total = len(sessions)
        avg_focus = round(sum(float(s.get("avg_focus_score", 0.0)) for s in sessions) / total, 1)
        avg_rolling = round(sum(float(s.get("avg_rolling_score", 0.0)) for s in sessions) / total, 1)
        total_alerts = int(sum(int(s.get("alerts_count", 0)) for s in sessions))
        last_status = sessions[0].get("final_status", "n/a")

        status_breakdown: Dict[str, int] = {}
        for session in sessions:
            status = str(session.get("final_status", "unknown"))
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        risk_band, risk_reason = self._derive_risk_band(
            avg_focus=avg_focus,
            total_alerts=total_alerts,
            total_sessions=total,
        )
        trend = self._derive_trend(sessions)

        return {
            "total_sessions": total,
            "avg_focus_score": avg_focus,
            "avg_rolling_score": avg_rolling,
            "total_alerts": total_alerts,
            "last_status": last_status,
            "status_breakdown": status_breakdown,
            "risk_band": risk_band,
            "risk_reason": risk_reason,
            "trend": trend,
        }

    def _derive_risk_band(self, *, avg_focus: float, total_alerts: int, total_sessions: int) -> tuple[str, str]:
        """Classify student into low/medium/high risk from focus sessions."""
        alerts_per_session = (total_alerts / total_sessions) if total_sessions > 0 else 0.0

        if avg_focus >= 80 and alerts_per_session <= 0.5:
            return "low", "Strong average focus and low alert frequency."
        if avg_focus >= 60 and alerts_per_session <= 1.5:
            return "medium", "Moderate focus with manageable alert frequency."
        return "high", "Low focus average or frequent alerts need intervention."

    def _derive_trend(self, sessions: List[Dict[str, Any]]) -> str:
        """Estimate trend (improving/declining/stable) from recent sessions."""
        if len(sessions) < 4:
            return "insufficient-data"

        # sessions are newest first. Compare recent block vs older block.
        recent_scores = [float(s.get("avg_focus_score", 0.0)) for s in sessions[:3]]
        older_scores = [float(s.get("avg_focus_score", 0.0)) for s in sessions[3:6]]
        if not older_scores:
            return "insufficient-data"

        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = sum(older_scores) / len(older_scores)
        delta = recent_avg - older_avg

        if delta >= 5:
            return "improving"
        if delta <= -5:
            return "declining"
        return "stable"
