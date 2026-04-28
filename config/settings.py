"""
Application configuration settings
Extracted from constants across all modules
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

def get_config_value(key, default=None):
    """
    Config from environment only (python-dotenv loads .env into os.environ at import time).
    Do not use st.secrets here — it can re-enter Streamlit and cause RecursionError.
    For Streamlit Cloud, set variables in the dashboard or use secrets.toml → env injection.
    """
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value
    return default


def _get_bool_config(key: str, default: str = "false") -> bool:
    return get_config_value(key, default).lower() in ("1", "true", "yes")

# Base paths
BASE_DIR = Path(__file__).parent.parent
DB_FILE = BASE_DIR / "data" / "attendance.db"
STATIC_DIR = BASE_DIR / "static"

# Security constants.
# These intentionally do not have hardcoded production fallbacks. The app validates
# them during startup before admin/bootstrap work can run.
APP_ENV = get_config_value("APP_ENV", "development").lower()
SALT = get_config_value("SALT")
SECRET_KEY = get_config_value("SECRET_KEY")
TOKEN_EXPIRY_HOURS = int(get_config_value("TOKEN_EXPIRY_HOURS", "1"))
MIN_PASSWORD_LENGTH = int(get_config_value("MIN_PASSWORD_LENGTH", "6"))
# Admin TOTP (Google Authenticator–compatible); off by default
ENABLE_ADMIN_2FA = _get_bool_config("ENABLE_ADMIN_2FA", "false")
# Password reset abuse control
PASSWORD_RESET_MAX_PER_HOUR = int(get_config_value("PASSWORD_RESET_MAX_PER_HOUR", "5"))

# Admin credentials. Required before first admin bootstrap.
ADMIN_EMAIL = get_config_value("ADMIN_EMAIL")
ADMIN_PASSWORD = get_config_value("ADMIN_PASSWORD")
ADMIN_ROLE = get_config_value("ADMIN_ROLE", "admin")

# Face recognition constants
MODEL_NAME = get_config_value("MODEL_NAME", "ArcFace")
DETECTOR_BACKEND = get_config_value("DETECTOR_BACKEND", "retinaface")
EMBEDDING_SIZE = int(get_config_value("EMBEDDING_SIZE", "512"))
RECOGNITION_THRESHOLD = float(get_config_value("RECOGNITION_THRESHOLD", "0.5"))
# Minimum gap between best and second-best *student* similarity (reduces lookalike swaps).
RECOGNITION_MARGIN = float(get_config_value("RECOGNITION_MARGIN", "0.08"))
# When false, do not embed the whole frame without a face box (safer; may require clearer photos).
ALLOW_SKIP_DETECTION_FALLBACK = get_config_value(
    "ALLOW_SKIP_DETECTION_FALLBACK", "false"
).lower() in ("1", "true", "yes")

# Biometric data controls
BIOMETRIC_CACHE_ENABLED = _get_bool_config("BIOMETRIC_CACHE_ENABLED", "false")
BIOMETRIC_CACHE_ENCRYPTION_KEY = get_config_value("BIOMETRIC_CACHE_ENCRYPTION_KEY")
BIOMETRIC_CACHE_FILE = get_config_value("BIOMETRIC_CACHE_FILE", "embeddings.cache")
BIOMETRIC_RETENTION_DAYS = int(get_config_value("BIOMETRIC_RETENTION_DAYS", "365"))
BIOMETRIC_HARD_DELETE_ON_STUDENT_DELETE = _get_bool_config(
    "BIOMETRIC_HARD_DELETE_ON_STUDENT_DELETE",
    "true",
)

# UI settings
PAGE_TITLE = "👁️ EyeAmHere — AI Attendance"
PAGE_ICON = "🎓"
LAYOUT = "wide"
SIDEBAR_STATE = "expanded"

# Database settings
DB_TIMEOUT = int(get_config_value("DB_TIMEOUT", "30"))
ENABLE_FOREIGN_KEYS = True

# Streamlit session keys
SESSION_KEYS = {
    'LOGIN_STATUS': 'login_status',
    'USERNAME': 'username', 
    'USER_ROLE': 'user_role',
    'USER_EMAIL': 'user_email'
}

# Email validation pattern
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Live mask WebRTC (process every Nth frame for CPU; higher = lighter)
MASK_FRAME_SKIP = int(get_config_value("MASK_FRAME_SKIP", "2"))

# Block attendance if mask detector is not confident the face is uncovered
MASK_BLOCK_UNCERTAIN = _get_bool_config("MASK_BLOCK_UNCERTAIN", "false")
# Minimum confidence required before attendance is blocked as MASK.
MASK_ATTENDANCE_BLOCK_CONFIDENCE = float(
    get_config_value("MASK_ATTENDANCE_BLOCK_CONFIDENCE", "0.75")
)

# Run mask / covering check before face recognition at attendance
ATTENDANCE_MASK_CHECK_ENABLED = _get_bool_config("ATTENDANCE_MASK_CHECK_ENABLED", "true")

# Focus / energy monitoring
FOCUS_MONITORING_ENABLED = _get_bool_config("FOCUS_MONITORING_ENABLED", "true")
FOCUS_ALERT_THRESHOLD = float(get_config_value("FOCUS_ALERT_THRESHOLD", "45"))
FOCUS_WARNING_THRESHOLD = float(get_config_value("FOCUS_WARNING_THRESHOLD", "70"))
FOCUS_MIN_FACE_RATIO = float(get_config_value("FOCUS_MIN_FACE_RATIO", "0.08"))
FOCUS_MAX_BLUR_ALERT = float(get_config_value("FOCUS_MAX_BLUR_ALERT", "120.0"))
FOCUS_AVERAGE_WINDOW = int(get_config_value("FOCUS_AVERAGE_WINDOW", "15"))

# Passive AI webcam attendance
PASSIVE_ATTENDANCE_ENABLED = _get_bool_config("PASSIVE_ATTENDANCE_ENABLED", "true")
PASSIVE_FRAME_SKIP = int(get_config_value("PASSIVE_FRAME_SKIP", "3"))
PASSIVE_CONF_THRESHOLD = float(get_config_value("PASSIVE_CONF_THRESHOLD", "0.65"))
PASSIVE_CONSECUTIVE_FRAMES = int(get_config_value("PASSIVE_CONSECUTIVE_FRAMES", "3"))
PASSIVE_MIN_VISIBLE_SECONDS = float(get_config_value("PASSIVE_MIN_VISIBLE_SECONDS", "10"))
PASSIVE_ATTENDANCE_COOLDOWN_SECONDS = int(get_config_value("PASSIVE_ATTENDANCE_COOLDOWN_SECONDS", "60"))
PASSIVE_ROLLING_WINDOW = int(get_config_value("PASSIVE_ROLLING_WINDOW", "5"))
PASSIVE_TRACK_MAX_MISSED = int(get_config_value("PASSIVE_TRACK_MAX_MISSED", "6"))
PASSIVE_TRACK_DISTANCE_PX = int(get_config_value("PASSIVE_TRACK_DISTANCE_PX", "90"))

# YOLO-World (pretrained, no training) — mask vs no-mask via open vocabulary
MASK_USE_YOLO = _get_bool_config("MASK_USE_YOLO", "true")
MASK_YOLO_MODEL = get_config_value("MASK_YOLO_MODEL", "yolov8s-worldv2.pt")
MASK_YOLO_DEVICE = get_config_value("MASK_YOLO_DEVICE", "cpu")
MASK_YOLO_CONF_MASK = float(get_config_value("MASK_YOLO_CONF_MASK", "0.22"))
MASK_YOLO_CONF_NOMASK = float(get_config_value("MASK_YOLO_CONF_NOMASK", "0.32"))
YOLO_CLASS_MASK_TEXT = get_config_value(
    "YOLO_CLASS_MASK_TEXT",
    "person wearing a medical face mask covering nose and mouth",
)
YOLO_CLASS_NOMASK_TEXT = get_config_value(
    "YOLO_CLASS_NOMASK_TEXT",
    "human face without mask nose and mouth visible",
)


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing or unsafe."""


def validate_security_config() -> None:
    """Fail fast on missing or known-unsafe security settings."""
    required = {
        "SECRET_KEY": SECRET_KEY,
        "SALT": SALT,
        "ADMIN_EMAIL": ADMIN_EMAIL,
        "ADMIN_PASSWORD": ADMIN_PASSWORD,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ConfigurationError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Create a .env file from .env.example before starting the app."
        )

    unsafe_values = {
        "attendance_system_salt_2024",
        "smart_attendance_secret_key_2024",
        "admin123",
        "password",
        "changeme",
    }
    unsafe = [
        key
        for key, value in required.items()
        if isinstance(value, str) and value.strip().lower() in unsafe_values
    ]
    if unsafe:
        raise ConfigurationError(
            "Unsafe default-like values detected for: "
            + ", ".join(unsafe)
            + ". Replace them with strong unique secrets."
        )

    if len(SECRET_KEY) < 32:
        raise ConfigurationError("SECRET_KEY must be at least 32 characters.")
    if len(SALT) < 16:
        raise ConfigurationError("SALT must be at least 16 characters.")
    if len(ADMIN_PASSWORD) < max(MIN_PASSWORD_LENGTH, 12):
        raise ConfigurationError(
            f"ADMIN_PASSWORD must be at least {max(MIN_PASSWORD_LENGTH, 12)} characters."
        )

    if BIOMETRIC_CACHE_ENABLED and not BIOMETRIC_CACHE_ENCRYPTION_KEY:
        raise ConfigurationError(
            "BIOMETRIC_CACHE_ENABLED=true requires BIOMETRIC_CACHE_ENCRYPTION_KEY "
            "so face embeddings are not cached in plaintext."
        )
    if BIOMETRIC_CACHE_ENABLED:
        try:
            from cryptography.fernet import Fernet

            Fernet(BIOMETRIC_CACHE_ENCRYPTION_KEY.encode("utf-8"))
        except Exception as exc:
            raise ConfigurationError(
                "BIOMETRIC_CACHE_ENCRYPTION_KEY must be a valid Fernet key. "
                "Generate one with: python -c \"from cryptography.fernet import "
                "Fernet; print(Fernet.generate_key().decode())\""
            ) from exc
