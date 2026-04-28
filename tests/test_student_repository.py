"""Student repository lifecycle regression tests."""

import numpy as np

import database.connection as db_connection
import database.student_repository as student_repository_module
from database.connection import init_database
from database.connection import get_db_connection
from database.student_repository import StudentRepository


def test_delete_student_by_roll_soft_deletes_and_hides_embeddings(tmp_path, monkeypatch):
    db_file = tmp_path / "attendance.db"
    monkeypatch.setattr(db_connection, "DB_FILE", db_file)

    init_database()

    repo = StudentRepository()
    embedding = np.ones(512, dtype=np.float32)
    success, message = repo.add_student_with_photos(
        name="Alice Example",
        roll_number="CS001",
        email="alice@example.com",
        phone="",
        course="Computer Science",
        embeddings_data=[("photo-1", embedding)],
    )
    assert success, message
    assert len(repo.get_all_students()) == 1
    assert len(repo.get_student_embeddings()) == 1

    success, message = repo.delete_student_by_roll("CS001")
    assert success, message
    assert repo.get_all_students() == []
    assert repo.get_student_embeddings() == []


def test_delete_student_by_roll_reports_missing_student(tmp_path, monkeypatch):
    db_file = tmp_path / "attendance.db"
    monkeypatch.setattr(db_connection, "DB_FILE", db_file)

    init_database()

    success, message = StudentRepository().delete_student_by_roll("MISSING")

    assert success is False
    assert "not found" in message.lower()


def test_purge_inactive_biometrics_removes_retained_embeddings(tmp_path, monkeypatch):
    db_file = tmp_path / "attendance.db"
    monkeypatch.setattr(db_connection, "DB_FILE", db_file)
    monkeypatch.setattr(student_repository_module, "BIOMETRIC_HARD_DELETE_ON_STUDENT_DELETE", False)

    init_database()

    repo = StudentRepository()
    embedding = np.ones(512, dtype=np.float32)
    success, message = repo.add_student_with_photos(
        name="Bob Example",
        roll_number="CS002",
        email="bob@example.com",
        phone="",
        course="Computer Science",
        embeddings_data=[("photo-2", embedding)],
    )
    assert success, message

    success, message = repo.delete_student_by_roll("CS002")
    assert success, message

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET deleted_at = '2000-01-01 00:00:00' WHERE roll_number = 'CS002'")
        conn.commit()

    deleted_count, message = repo.purge_inactive_biometrics(retention_days=1)
    assert deleted_count == 1
    assert "purged" in message.lower()
