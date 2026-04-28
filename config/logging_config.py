"""
Centralized logging configuration
Extracted from logging setup across modules
"""
import logging
import sys
from pathlib import Path

from config.settings import BASE_DIR


def setup_logging(level=logging.INFO, log_file=None):
    """Set up application-wide logging configuration.

    By default, logs are written both to stdout and to logs/system.log.
    """
    # Determine log file path
    if log_file is None:
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "system.log"

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
            except Exception:
                pass

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid attaching duplicate handlers if setup_logging is called multiple times
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if not any(
        isinstance(h, logging.FileHandler)
        and isinstance(getattr(h, "baseFilename", None), str)
        and h.baseFilename.endswith(str(log_file))
        for h in root_logger.handlers
    ):
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress third-party logging noise
    logging.getLogger("deepface").setLevel(logging.WARNING)
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    return root_logger


# Initialize logging
logger = setup_logging()

