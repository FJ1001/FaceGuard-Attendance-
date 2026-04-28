"""Tests for rolling average focus alerts in the live processor."""

from face_focus.webrtc_processor import FocusEnergyVideoProcessor


def test_live_processor_builds_rolling_average_alerts():
    processor = FocusEnergyVideoProcessor(frame_skip=1, average_window=5)

    processor._record_analysis({"focus_score": 80.0, "status": "focused", "alerts": ["ok"]})
    processor._record_analysis({"focus_score": 60.0, "status": "attention", "alerts": ["ok"]})
    processor._record_analysis({"focus_score": 40.0, "status": "critical", "alerts": ["ok"]})
    processor._record_analysis({"focus_score": 30.0, "status": "critical", "alerts": ["ok"]})
    latest = processor._record_analysis({"focus_score": 20.0, "status": "critical", "alerts": ["ok"]})

    assert latest["sample_count"] == 5
    assert latest["rolling_focus_score"] == 46.0
    assert latest["rolling_status"] == "attention"
    assert any("average focus is moderate" in alert.lower() for alert in latest["rolling_alerts"])


def test_live_processor_marks_low_average_as_critical():
    processor = FocusEnergyVideoProcessor(frame_skip=1, average_window=4)

    latest = None
    for score in (20.0, 25.0, 30.0, 35.0):
        latest = processor._record_analysis({"focus_score": score, "status": "critical", "alerts": ["ok"]})

    assert latest is not None
    assert latest["rolling_focus_score"] == 27.5
    assert latest["rolling_status"] == "critical"
    assert any("average focus is low" in alert.lower() for alert in latest["rolling_alerts"])