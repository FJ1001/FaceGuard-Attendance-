"""
Embedding cache utilities.

SQLite remains the source of truth. The disk cache is disabled by default because
face embeddings are biometric data; when enabled, cache bytes are encrypted.
"""

import io
import logging
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np

from config.settings import (
    BASE_DIR,
    BIOMETRIC_CACHE_ENABLED,
    BIOMETRIC_CACHE_ENCRYPTION_KEY,
    BIOMETRIC_CACHE_FILE,
    EMBEDDING_SIZE,
)
from utils.face_utils import ensure_dir_exists

logger = logging.getLogger(__name__)

# Cache file location: data/embeddings.cache (encrypted when enabled)
EMBEDDINGS_FILE: Path = BASE_DIR / "data" / BIOMETRIC_CACHE_FILE
LEGACY_EMBEDDINGS_FILE: Path = BASE_DIR / "data" / "embeddings.npy"


def get_cache_path() -> Path:
    """Return the path to the embeddings cache file."""
    return EMBEDDINGS_FILE


def _fernet():
    if not BIOMETRIC_CACHE_ENCRYPTION_KEY:
        return None
    from cryptography.fernet import Fernet

    return Fernet(BIOMETRIC_CACHE_ENCRYPTION_KEY.encode("utf-8"))


def _serialize_records(records: list) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, np.array(records, dtype=object))
    return buffer.getvalue()


def _deserialize_records(payload: bytes):
    buffer = io.BytesIO(payload)
    return np.load(buffer, allow_pickle=True)


def save_embeddings_cache(student_embeddings: List[Tuple[int, str, str, np.ndarray]]) -> Optional[Path]:
    """
    Persist student embeddings to the encrypted cache when enabled.

    The cache format is a NumPy object array of dicts:
    {
        "student_id": int,
        "name": str,
        "roll_number": str,
        "embedding": np.ndarray (float32, length EMBEDDING_SIZE)
    }
    """
    if not BIOMETRIC_CACHE_ENABLED:
        clear_embeddings_cache()
        return None

    cipher = _fernet()
    if cipher is None:
        logger.warning("Embedding cache skipped: encryption key is not configured")
        clear_embeddings_cache()
        return None

    ensure_dir_exists(EMBEDDINGS_FILE.parent)

    records = []
    for student_id, name, roll_number, embedding in student_embeddings:
        # Ensure ndarray and correct dtype/size
        emb_arr = np.asarray(embedding, dtype=np.float32)
        if emb_arr.shape[0] != EMBEDDING_SIZE:
            # Pad or truncate to expected size, without mutating original
            fixed = np.zeros(EMBEDDING_SIZE, dtype=np.float32)
            size = min(EMBEDDING_SIZE, emb_arr.shape[0])
            fixed[:size] = emb_arr[:size]
            emb_arr = fixed

        records.append(
            {
                "student_id": int(student_id),
                "name": str(name),
                "roll_number": str(roll_number),
                "embedding": emb_arr,
            }
        )

    plaintext = _serialize_records(records)
    EMBEDDINGS_FILE.write_bytes(cipher.encrypt(plaintext))
    return EMBEDDINGS_FILE


def load_embeddings_cache() -> Optional[List[Tuple[int, str, str, np.ndarray]]]:
    """
    Load embeddings from the encrypted cache, if enabled and available.

    Returns a list of (student_id, name, roll_number, embedding) tuples,
    or None if the cache file does not exist or is invalid.
    """
    if not BIOMETRIC_CACHE_ENABLED:
        clear_embeddings_cache()
        return None

    if not EMBEDDINGS_FILE.exists():
        return None

    try:
        cipher = _fernet()
        if cipher is None:
            clear_embeddings_cache()
            return None

        raw = _deserialize_records(cipher.decrypt(EMBEDDINGS_FILE.read_bytes()))
        student_embeddings: List[Tuple[int, str, str, np.ndarray]] = []

        for item in raw:
            if not isinstance(item, dict):
                continue

            emb = np.asarray(item.get("embedding"), dtype=np.float32)
            if emb.shape[0] != EMBEDDING_SIZE:
                fixed = np.zeros(EMBEDDING_SIZE, dtype=np.float32)
                size = min(EMBEDDING_SIZE, emb.shape[0])
                fixed[:size] = emb[:size]
                emb = fixed

            student_embeddings.append(
                (
                    int(item.get("student_id")),
                    str(item.get("name")),
                    str(item.get("roll_number")),
                    emb,
                )
            )

        return student_embeddings

    except Exception as exc:
        # If anything goes wrong, treat cache as unavailable
        logger.warning("Embedding cache unavailable: %s", exc)
        return None


def clear_embeddings_cache() -> None:
    """Remove the embeddings cache file if it exists."""
    for cache_file in (EMBEDDINGS_FILE, LEGACY_EMBEDDINGS_FILE):
        try:
            if cache_file.exists():
                cache_file.unlink()
        except Exception:
            # Cache is an optimization, not critical.
            pass

