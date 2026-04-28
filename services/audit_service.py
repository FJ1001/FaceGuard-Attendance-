"""Thin wrapper for audit logging (safe no-op on failure)."""

from typing import Any, Optional

from database.audit_repository import append_audit


def log(
    action: str,
    actor_email: Optional[str] = None,
    *,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Any = None,
    client_hint: Optional[str] = None,
) -> None:
    append_audit(
        action=action,
        actor_email=actor_email or "system",
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        client_hint=client_hint,
    )
