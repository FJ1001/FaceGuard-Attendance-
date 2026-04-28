"""Recognition decision logic (margin + threshold) with mocked embedding."""

from unittest.mock import patch

import numpy as np
import pytest

from face_recognition.recognition_engine import FaceRecognitionEngine


@pytest.fixture
def engine():
    with patch.object(FaceRecognitionEngine, "_initialize_models", lambda self: None):
        e = FaceRecognitionEngine()
        e.recognition_threshold = 0.5
        e.recognition_margin = 0.08
        return e


def _norm(v):
    v = np.asarray(v, dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


def test_single_student_threshold_pass(engine):
    probe = _norm(np.random.randn(512))
    known = [(1, "Alice", "01", probe.copy())]
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    with patch.object(engine, "generate_embedding", return_value=probe):
        ok, info, conf, meta = engine.recognize_face(img, known)
    assert ok is True
    assert info["student_id"] == 1
    assert meta["reason"] == "matched"
    assert meta["threshold"] == engine.recognition_threshold
    assert meta["required_margin"] == engine.recognition_margin


def test_low_confidence(engine):
    probe = _norm(np.random.randn(512))
    stranger = _norm(np.random.randn(512))
    known = [(1, "Alice", "01", stranger)]
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    with patch.object(engine, "generate_embedding", return_value=probe):
        ok, info, conf, meta = engine.recognize_face(img, known)
    assert ok is False
    assert meta["reason"] == "low_confidence"


def test_ambiguous_two_students(engine):
    probe = _norm(np.ones(512))
    # Two templates almost identical to probe → top-2 students stay very close in score
    t1 = probe.copy()
    t2 = _norm(probe + np.random.default_rng(0).standard_normal(512) * 0.0005)
    known = [(1, "A", "1", t1), (2, "B", "2", t2)]
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    with patch.object(engine, "generate_embedding", return_value=probe):
        ok, info, conf, meta = engine.recognize_face(img, known)
    assert ok is False
    assert meta["reason"] == "ambiguous"


def test_multi_template_max_per_student(engine):
    probe = _norm(np.array([1.0] + [0.0] * 511))
    good = probe.copy()
    bad = _norm(np.random.randn(512))
    known = [(7, "Bob", "2", bad), (7, "Bob", "2", good)]
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    with patch.object(engine, "generate_embedding", return_value=probe):
        ok, info, conf, meta = engine.recognize_face(img, known)
    assert ok is True
    assert info["student_id"] == 7


def test_validate_embedding_quality(engine):
    valid = _norm(np.random.randn(512))
    ok, message = engine.validate_embedding_quality(valid)

    assert ok is True
    assert message == "Embedding is valid"


def test_validate_embedding_quality_rejects_wrong_size(engine):
    invalid = np.ones(128, dtype=np.float32)
    ok, message = engine.validate_embedding_quality(invalid)

    assert ok is False
    assert "expected 512" in message
