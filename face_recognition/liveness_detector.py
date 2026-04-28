"""
liveness_detector.py — Passive liveness / anti-spoofing scoring.

Analyses a face crop using purely classical OpenCV features:
  1. Texture richness  — Laplacian variance of the face region
  2. Specular highlights — bright specular spots (eyes/nose) expected on real faces
  3. Edge density       — real faces have fine edges; printed photos are softer
  4. Colour naturalness — skin-tone distribution check (not a uniform colour block)

Returns a LivenessResult with score 0–100 and a human-readable label.
No neural network, no internet, < 5 ms on CPU.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
class LivenessResult:
    """Container for a liveness check outcome."""

    def __init__(self, score: float, label: str, detail: dict):
        self.score = score          # 0–100
        self.label = label          # "Live", "Suspicious", "Likely Spoof"
        self.detail = detail        # per-component breakdown

    def __repr__(self):
        return f"LivenessResult(score={self.score:.1f}, label={self.label!r})"


# ────────────────────────────────────────────────────────────────────────────
def _crop_face(image: np.ndarray) -> np.ndarray:
    """Try to isolate the face region; fall back to full image."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return image
        gray_eq = cv2.equalizeHist(gray)
        faces = cascade.detectMultiScale(gray_eq, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
        if len(faces) == 1:
            x, y, w, h = faces[0]
            return image[y : y + h, x : x + w]
    except Exception:
        pass
    return image


def _texture_score(face_gray: np.ndarray) -> float:
    """Laplacian variance — higher means more fine texture (real face)."""
    lap_var = cv2.Laplacian(face_gray, cv2.CV_64F).var()
    # Empirically: real face ≥ 200, printed photo ≈ 50–100, screen ≈ 60–150
    # Map to 0–100 with soft clamp
    score = min(100.0, max(0.0, (lap_var - 50) / 4.5))
    return round(score, 1)


def _specular_score(face_gray: np.ndarray) -> float:
    """Bright specular highlights (whites of eyes, bridge of nose, forehead).
    Real faces under normal lighting have 1–4 specular blobs; flat photos fewer.
    """
    _, thresh = cv2.threshold(face_gray, 230, 255, cv2.THRESH_BINARY)
    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(thresh, connectivity=8)
    # Count blobs between 10–500 px² (skip background label 0)
    valid_blobs = sum(
        1 for i in range(1, n_labels)
        if 10 <= stats[i, cv2.CC_STAT_AREA] <= 500
    )
    # 0 blobs → 20, 2–5 blobs → 100, many blobs → 60 (screen glare)
    if valid_blobs == 0:
        return 20.0
    elif valid_blobs <= 5:
        return min(100.0, 40.0 + valid_blobs * 12.0)
    else:
        return max(40.0, 100.0 - (valid_blobs - 5) * 5.0)


def _edge_density_score(face_gray: np.ndarray) -> float:
    """Canny edge density — real faces have rich, fine edges."""
    edges = cv2.Canny(face_gray, 50, 150)
    density = np.count_nonzero(edges) / edges.size
    # density ≥ 0.08 → strong edges, < 0.02 → very flat
    score = min(100.0, max(0.0, density * 1000))
    return round(score, 1)


def _colour_naturalness_score(face_bgr: np.ndarray) -> float:
    """Check that the face area contains a spread of skin-like colours,
    not a uniform block (e.g. a phone screen showing a single still image often
    clips highlights/shadows differently).
    """
    try:
        hsv = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2HSV)
        # Skin: H ∈ [0,25] or [160,180], S ∈ [20,200], V ∈ [50,230]
        lower1 = np.array([0, 20, 50], dtype=np.uint8)
        upper1 = np.array([25, 200, 230], dtype=np.uint8)
        lower2 = np.array([160, 20, 50], dtype=np.uint8)
        upper2 = np.array([180, 200, 230], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower1, upper1) | cv2.inRange(hsv, lower2, upper2)
        skin_ratio = np.count_nonzero(mask) / mask.size
        # std of V channel within skin mask — real faces have mid-range std
        v_channel = hsv[:, :, 2]
        skin_values = v_channel[mask > 0]
        if len(skin_values) < 50:
            return 40.0  # too little skin detected
        v_std = float(np.std(skin_values))
        # Good range: std 20–60; flat photo: < 15
        naturalness = min(100.0, max(0.0, v_std * 2.0))
        # Weight by skin presence
        presence_score = min(100.0, skin_ratio * 400)
        return round((naturalness * 0.6 + presence_score * 0.4), 1)
    except Exception:
        return 50.0


# ────────────────────────────────────────────────────────────────────────────
def compute_liveness_score(image: np.ndarray) -> LivenessResult:
    """Main entry point.  Pass any BGR OpenCV image; returns LivenessResult.
    
    Usage:
        result = compute_liveness_score(frame)
        print(result.score, result.label)
    """
    if image is None or image.size == 0:
        return LivenessResult(0.0, "Error", {"error": "empty image"})

    try:
        # Ensure BGR uint8
        if image.dtype != np.uint8:
            image = np.clip(image * 255, 0, 255).astype(np.uint8)
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        face = _crop_face(image)
        face_resized = cv2.resize(face, (128, 128))
        gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)

        tex   = _texture_score(gray)
        spec  = _specular_score(gray)
        edge  = _edge_density_score(gray)
        color = _colour_naturalness_score(face_resized)

        # Weighted composite
        score = round(tex * 0.35 + spec * 0.20 + edge * 0.25 + color * 0.20, 1)
        score = max(0.0, min(100.0, score))

        if score >= 68:
            label = "Live"
        elif score >= 45:
            label = "Suspicious"
        else:
            label = "Likely Spoof"

        detail = {
            "texture": tex,
            "specular_highlights": spec,
            "edge_density": edge,
            "colour_naturalness": color,
            "composite": score,
        }

        return LivenessResult(score, label, detail)

    except Exception as e:
        logger.error("Liveness detection error: %s", e)
        return LivenessResult(50.0, "Unknown", {"error": str(e)})
