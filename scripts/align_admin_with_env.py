"""
One-time fix: set the admin user's email and password from .env (ADMIN_EMAIL, ADMIN_PASSWORD).

Use when the DB was created with an old hardcoded email (e.g. admin@attendance.com) but you want
to log in with values from .env.

Run from project root:
  python scripts/align_admin_with_env.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import ADMIN_EMAIL, ADMIN_PASSWORD
from auth.password_hashing import hash_password
from database.connection import get_db_connection


def main() -> None:
    new_hash = hash_password(ADMIN_PASSWORD)
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, email FROM users WHERE role = 'admin' ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if not row:
            print("No admin user found. Start the app once to create the database, or register an admin.")
            sys.exit(1)
        uid = row["id"]
        old_email = row["email"]
        cur.execute(
            "UPDATE users SET email = ?, password_hash = ? WHERE id = ?",
            (ADMIN_EMAIL, new_hash, uid),
        )
        conn.commit()
    print(f"Updated admin id={uid}: email {old_email!r} -> {ADMIN_EMAIL!r}")
    print("Password set from ADMIN_PASSWORD in your environment / .env")


if __name__ == "__main__":
    main()
