"""
Password hashing: bcrypt for new passwords, SHA-256+salt verification for legacy rows.
Successful login with a legacy hash upgrades the stored hash to bcrypt.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Tuple

import bcrypt

# Load via env only — avoids importing config.settings (Streamlit) during auth
SALT = os.getenv("SALT", "attendance_system_salt_2024")

logger = logging.getLogger(__name__)

_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def _is_bcrypt_hash(stored: str) -> bool:
    return bool(stored) and stored.startswith(_BCRYPT_PREFIXES)


def hash_password(password: str) -> str:
    """Hash password with bcrypt (cost factor 12)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify password. Supports bcrypt hashes and legacy SHA-256 hex (64 chars) with global SALT.
    """
    if not stored_hash or password is None:
        return False
    if _is_bcrypt_hash(stored_hash):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))
        except Exception:
            return False
    # Legacy: SHA-256(salt + password) — old code used (password + SALT)
    legacy = hashlib.sha256((password + SALT).encode()).hexdigest()
    if legacy == stored_hash:
        return True
    return False


def is_legacy_sha256_hash(stored_hash: str) -> bool:
    """True if this looks like the old hex digest (not bcrypt)."""
    if not stored_hash or _is_bcrypt_hash(stored_hash):
        return False
    return len(stored_hash) == 64 and all(c in "0123456789abcdefABCDEF" for c in stored_hash)
