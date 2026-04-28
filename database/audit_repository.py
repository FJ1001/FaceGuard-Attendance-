"""Append-only audit log."""

import json
import logging
from typing import Any, Dict, List, Optional

from database.connection import get_db_connection

logger = logging.getLogger(__name__)


def append_audit(
    action: str,
    actor_email: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Any = None,
    client_hint: Optional[str] = None,
) -> None:
    try:
        detail_str = None
        if detail is not None:
            if isinstance(detail, str):
                detail_str = detail[:4000]
            else:
                detail_str = json.dumps(detail, default=str)[:4000]
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO audit_log (actor_email, action, target_type, target_id, detail, client_hint)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (actor_email, action, target_type, target_id, detail_str, client_hint),
            )
            conn.commit()
    except Exception as e:
        logger.warning("audit_log write failed: %s", e)


def list_recent_audit(limit: int = 200) -> List[Dict]:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, created_at, actor_email, action, target_type, target_id, detail, client_hint
                FROM audit_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error("list_recent_audit: %s", e)
        return []
