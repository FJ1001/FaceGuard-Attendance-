"""System health probes (disk, models, database file)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List

from config.settings import BASE_DIR, DB_FILE, MASK_YOLO_MODEL


def disk_free_gb(path: Path | None = None) -> float:
    root = path or BASE_DIR
    try:
        usage = shutil.disk_usage(root)
        return round(usage.free / (1024**3), 2)
    except Exception:
        return 0.0


def check_model_files() -> List[Dict[str, Any]]:
    """Report presence of common weight files under project root."""
    candidates = [
        BASE_DIR / MASK_YOLO_MODEL,
        BASE_DIR / "yolov8n.pt",
        BASE_DIR / "data",
    ]
    out = []
    for p in candidates:
        if p.is_dir():
            out.append({"path": str(p), "exists": p.exists(), "type": "dir"})
        else:
            out.append(
                {
                    "path": str(p),
                    "exists": p.is_file(),
                    "type": "file",
                    "size_mb": round(p.stat().st_size / (1024**2), 2) if p.is_file() else None,
                }
            )
    return out


def database_status() -> Dict[str, Any]:
    exists = DB_FILE.is_file()
    size_mb = round(DB_FILE.stat().st_size / (1024**2), 2) if exists else 0
    return {"path": str(DB_FILE), "exists": exists, "size_mb": size_mb}
