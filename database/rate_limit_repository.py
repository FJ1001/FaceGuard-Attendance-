"""Rate limiting for password reset (per email, rolling window)."""

import logging

from database.connection import get_db_connection

logger = logging.getLogger(__name__)


def count_password_reset_attempts(email: str, hours: int = 1) -> int:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT COUNT(*) FROM password_reset_rate
                WHERE email = ?
                  AND datetime(created_at) >= datetime('now', '-{int(hours)} hour')
                """,
                (email.lower(),),
            )
            return int(cur.fetchone()[0])
    except Exception as e:
        logger.warning("count_password_reset_attempts: %s", e)
        return 0


def record_password_reset_attempt(email: str) -> None:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO password_reset_rate (email) VALUES (?)",
                (email.lower(),),
            )
            conn.commit()
    except Exception as e:
        logger.warning("record_password_reset_attempt: %s", e)
