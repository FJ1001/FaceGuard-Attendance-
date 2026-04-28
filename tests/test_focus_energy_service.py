"""Tests for the focus and energy monitoring service."""

import numpy as np

from face_focus.focus_energy_service import FocusEnergyService


def _service() -> FocusEnergyService:
    return FocusEnergyService()


def test_focus_energy_reports_critical_when_no_face(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "_detect_faces", lambda _gray: [])

    result = service.analyze_image(np.full((100, 100, 3), 128, dtype=np.uint8))

    assert result["status"] == "critical"
    assert result["focus_score"] == 0
    assert any("no face" in alert.lower() for alert in result["alerts"])


def test_focus_energy_scores_high_when_face_is_centered(monkeypatch):
    service = _service()
    monkeypatch.setattr("face_focus.focus_energy_service.FOCUS_MAX_BLUR_ALERT", 0.0)
    monkeypatch.setattr(service, "_detect_faces", lambda _gray: [(50, 50, 80, 80)])
    monkeypatch.setattr(service, "_detect_eyes", lambda _face_gray: 2)
    monkeypatch.setattr(service, "_brightness_component", lambda _brightness: 0.95)
    monkeypatch.setattr(service, "_clarity_component", lambda _clarity: 0.9)
    monkeypatch.setattr(service, "_centering_component", lambda _face_box, _shape: 0.92)
    monkeypatch.setattr(service, "_face_size_component", lambda _face_ratio: 0.88)

    result = service.analyze_image(np.full((200, 200, 3), 140, dtype=np.uint8))

    assert result["status"] == "focused"
    assert result["focus_score"] >= 80
    assert result["eye_count"] == 2
    assert result["alerts"] == ["Focus looks good."]


def test_focus_energy_alerts_on_low_quality_frame(monkeypatch):
    service = _service()
    monkeypatch.setattr(service, "_detect_faces", lambda _gray: [(5, 5, 40, 40)])
    monkeypatch.setattr(service, "_detect_eyes", lambda _face_gray: 0)
    monkeypatch.setattr(service, "_brightness_component", lambda _brightness: 0.2)
    monkeypatch.setattr(service, "_clarity_component", lambda _clarity: 0.1)
    monkeypatch.setattr(service, "_centering_component", lambda _face_box, _shape: 0.2)
    monkeypatch.setattr(service, "_face_size_component", lambda _face_ratio: 0.1)

    result = service.analyze_image(np.full((200, 200, 3), 40, dtype=np.uint8))

    assert result["status"] == "critical"
    assert result["focus_score"] < 45
    assert len(result["alerts"]) >= 3