"""Attendance lifecycle tests from recognition to IN/OUT marking."""

import numpy as np

import database.connection as db_connection
from database.connection import init_database
from database.student_repository import StudentRepository
from services.attendance_service import AttendanceService


def test_recognition_marks_time_in_then_time_out(tmp_path, monkeypatch):
    db_file = tmp_path / "attendance.db"
    monkeypatch.setattr(db_connection, "DB_FILE", db_file)

    init_database()

    student_repo = StudentRepository()
    embedding = np.ones(512, dtype=np.float32)
    success, message = student_repo.add_student_with_photos(
        name="Alice Example",
        roll_number="CS001",
        email="alice@example.com",
        phone="",
        course="Computer Science",
        embeddings_data=[("photo-1", embedding)],
    )
    assert success, message
    student_id = student_repo.get_all_students()[0]["id"]

    service = AttendanceService()

    def fake_recognize_student(_image):
        return (
            True,
            {"student_id": student_id, "name": "Alice Example", "roll_number": "CS001"},
            0.91,
            {"reason": "matched", "margin_achieved": 0.2, "second_similarity": 0.71},
        )

    monkeypatch.setattr(service.student_service, "recognize_student", fake_recognize_student)

    image = np.zeros((128, 128, 3), dtype=np.uint8)
    success, message, student_info = service.mark_attendance_by_recognition(
        image,
        marked_by="test_recognition",
    )
    assert success, message
    assert "Attendance marked" in message
    assert student_info["recognition_confidence"] == 0.91

    success, message, student_info = service.mark_attendance_by_recognition(
        image,
        marked_by="test_recognition",
    )
    assert success, message
    assert "Time-out marked" in message
    assert student_info["recognition_margin"] == 0.2

    records = service.get_attendance_records(student_id=student_id)
    assert len(records) == 1
    assert records[0]["time_in"]
    assert records[0]["time_out"]
