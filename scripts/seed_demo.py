"""
seed_demo.py — Populate the database with realistic demo data for live judging.

Run standalone:  python scripts/seed_demo.py
Or call from UI: from scripts.seed_demo import seed_demo_data; seed_demo_data()

Creates 6 synthetic students across different courses with 30 days of
realistic, varied attendance patterns (some excellent, some at-risk).
Uses randomly-generated-but-stable face embeddings (not real photo data).
"""
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import base64
import hashlib
import logging
import random
from datetime import date, datetime, timedelta
from typing import List, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# ── Demo student roster ──────────────────────────────────────────────────────
DEMO_STUDENTS = [
    {
        "name": "Ahmad Raza Khan",
        "roll": "CS2021-001",
        "email": "ahmad.raza@demo.local",
        "phone": "9876543210",
        "course": "CSE",
        # attendance rate ~92% — Excellent
        "profile": "excellent",
    },
    {
        "name": "Bilal Hussain Mir",
        "roll": "CS2021-002",
        "email": "bilal.mir@demo.local",
        "phone": "9876543211",
        "course": "CSE",
        # attendance rate ~78% — Good
        "profile": "good",
    },
    {
        "name": "Sara Kabir Wani",
        "roll": "EE2021-001",
        "email": "sara.wani@demo.local",
        "phone": "9876543212",
        "course": "EE",
        # attendance rate ~65% — Average
        "profile": "average",
    },
    {
        "name": "Umar Farooq Bhat",
        "roll": "CE2021-001",
        "email": "umar.bhat@demo.local",
        "phone": "9876543213",
        "course": "CE",
        # attendance rate ~38% — Poor / at-risk
        "profile": "poor",
    },
    {
        "name": "Zara Aslam Sheikh",
        "roll": "EE2021-002",
        "email": "zara.sheikh@demo.local",
        "phone": "9876543214",
        "course": "EE",
        # attendance rate ~95% — Excellent
        "profile": "excellent",
    },
    {
        "name": "Imran Yousuf Lone",
        "roll": "ME2021-001",
        "email": "imran.lone@demo.local",
        "phone": "9876543215",
        "course": "ME",
        # attendance rate ~55% — Average / borderline
        "profile": "average",
    },
]

PROFILE_RATES = {
    "excellent": 0.92,
    "good": 0.78,
    "average": 0.62,
    "poor": 0.38,
}


def _generate_stable_embedding(seed_str: str, size: int = 512) -> np.ndarray:
    """Produce a deterministic pseudo-random unit-norm embedding for a student.
    
    Uses SHA-256 of the seed string to derive a repeatable random state so
    demo embeddings are stable across reseeds.
    """
    digest = hashlib.sha256(seed_str.encode()).digest()
    seed_int = int.from_bytes(digest[:4], "big")
    rng = np.random.default_rng(seed_int)
    vec = rng.standard_normal(size).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _embedding_to_b64(embedding: np.ndarray) -> str:
    return base64.b64encode(embedding.tobytes()).decode("utf-8")


def seed_demo_data(days_back: int = 30) -> Tuple[bool, str]:
    """Insert demo students and attendance records.
    
    Idempotent — skips students whose roll_number already exists.
    Returns (success, message).
    """
    try:
        from database.connection import get_db_connection, init_database

        # Ensure schema exists
        init_database()

        with get_db_connection() as conn:
            conn.row_factory = __import__("sqlite3").Row
            cursor = conn.cursor()

            students_added = 0
            records_added = 0

            for student in DEMO_STUDENTS:
                # Skip if already exists
                cursor.execute(
                    "SELECT id FROM students WHERE roll_number = ?",
                    (student["roll"],),
                )
                existing = cursor.fetchone()

                if existing:
                    student_id = existing["id"]
                    logger.info("Student %s already exists — skipping insert", student["name"])
                else:
                    # Insert student
                    cursor.execute(
                        """
                        INSERT INTO students (name, roll_number, email, phone, course)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            student["name"],
                            student["roll"],
                            student["email"],
                            student["phone"],
                            student["course"],
                        ),
                    )
                    student_id = cursor.lastrowid

                    # Insert 3 embeddings per student (simulate 3 registered photos)
                    for photo_idx in range(3):
                        seed = f"{student['roll']}_{photo_idx}"
                        emb = _generate_stable_embedding(seed)
                        cursor.execute(
                            """
                            INSERT INTO face_embeddings (student_id, embedding_data, photo_id)
                            VALUES (?, ?, ?)
                            """,
                            (student_id, _embedding_to_b64(emb), f"{student['roll']}_photo_{photo_idx}"),
                        )

                    conn.commit()
                    students_added += 1
                    logger.info("Added student: %s (id=%s)", student["name"], student_id)

                # Seed attendance records for the past `days_back` days
                rate = PROFILE_RATES[student["profile"]]
                today = date.today()
                rng = random.Random(student["roll"])  # deterministic per student

                for offset in range(days_back, 0, -1):
                    record_date = today - timedelta(days=offset)
                    # Skip weekends
                    if record_date.weekday() >= 5:
                        continue

                    # Check if record already exists
                    cursor.execute(
                        "SELECT id FROM attendance WHERE student_id=? AND date=?",
                        (student_id, record_date.isoformat()),
                    )
                    if cursor.fetchone():
                        continue

                    if rng.random() < rate:
                        # Present: random check-in 8:30–9:30 AM
                        checkin_hour = 8
                        checkin_min = rng.randint(30, 89) % 60
                        if checkin_min >= 60:
                            checkin_hour = 9
                            checkin_min = checkin_min - 60
                        time_in = f"{checkin_hour:02d}:{checkin_min:02d}:00"

                        # ~70% also check out between 4–5 PM
                        time_out = None
                        if rng.random() < 0.70:
                            out_hour = rng.randint(16, 17)
                            out_min = rng.randint(0, 59)
                            time_out = f"{out_hour:02d}:{out_min:02d}:00"

                        cursor.execute(
                            """
                            INSERT INTO attendance (student_id, date, time_in, time_out, status, marked_by)
                            VALUES (?, ?, ?, ?, 'present', 'demo_seed')
                            """,
                            (student_id, record_date.isoformat(), time_in, time_out),
                        )
                        records_added += 1

                conn.commit()

            msg = (
                f"Demo data loaded: {students_added} new student(s) added, "
                f"{records_added} attendance record(s) seeded over {days_back} days."
            )
            logger.info(msg)
            return True, msg

    except Exception as e:
        logger.error("seed_demo_data failed: %s", e)
        return False, f"Error seeding demo data: {e}"


if __name__ == "__main__":
    ok, msg = seed_demo_data()
    print(msg)
    sys.exit(0 if ok else 1)
