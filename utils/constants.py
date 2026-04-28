"""
Application constants
Centralized constants used across the application
"""
from enum import Enum
from typing import Dict, List

# User Roles
class UserRole:
    ADMIN = 'admin'
    USER = 'user'
    STUDENT = 'student'

# Authentication Status
class AuthStatus:
    SUCCESS = 'success'
    FAILED = 'failed'
    INVALID_CREDENTIALS = 'invalid_credentials'
    USER_NOT_FOUND = 'user_not_found'
    TOKEN_EXPIRED = 'token_expired'

# Attendance Status
class AttendanceStatus:
    PRESENT = 'present'
    ABSENT = 'absent'
    LATE = 'late'
    EXCUSED = 'excused'

# Recognition Status
class RecognitionStatus:
    SUCCESS = 'success'
    FAILED = 'failed'
    NO_FACE_DETECTED = 'no_face_detected'
    MULTIPLE_FACES = 'multiple_faces'
    POOR_QUALITY = 'poor_quality'
    LOW_CONFIDENCE = 'low_confidence'

# File Types
ALLOWED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
ALLOWED_IMAGE_MIMES = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/tiff']

# Database Constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000

# Face Recognition Constants
MIN_FACE_SIZE = 50
MAX_FACE_SIZE = 1000
EMBEDDING_CACHE_SIZE = 1000
MAX_PHOTOS_PER_STUDENT = 5
MIN_PHOTOS_PER_STUDENT = 2

# UI Constants
SIDEBAR_WIDTH = 300
MAIN_CONTENT_PADDING = 2
METRIC_CARD_HEIGHT = 120

# Time Constants (in seconds)
SESSION_TIMEOUT = 24 * 60 * 60  # 24 hours
PASSWORD_RESET_TIMEOUT = 60 * 60  # 1 hour
CACHE_TIMEOUT = 30 * 60  # 30 minutes

# Validation Constants
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 30
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 128
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 100

# Course Constants
AVAILABLE_COURSES = [
    'CSE',  # Computer Science Engineering
    'CE',   # Civil Engineering  
    'EE',   # Electrical Engineering
    'ME',   # Mechanical Engineering
    'BE',   # Biotechnology Engineering
    'ECE',  # Electronics and Communication Engineering
    'IT',   # Information Technology
    'ETC',  # Electronics and Telecommunication
    'EXTC', # Electronics and Extc
    'AIDS', # Artificial Intelligence and Data Science
]

# Error Messages
ERROR_MESSAGES: Dict[str, str] = {
    'INVALID_EMAIL': 'Please enter a valid email address',
    'WEAK_PASSWORD': 'Password must be at least 6 characters long',
    'USER_EXISTS': 'User with this email already exists',
    'INVALID_LOGIN': 'Invalid email or password',
    'SESSION_EXPIRED': 'Your session has expired. Please login again',
    'UNAUTHORIZED': 'You are not authorized to perform this action',
    'STUDENT_EXISTS': 'Student with this roll number already exists',
    'NO_FACE_DETECTED': 'No face detected in the image',
    'MULTIPLE_FACES': 'Multiple faces detected. Please ensure only one face is visible',
    'POOR_IMAGE_QUALITY': 'Image quality is too poor for recognition',
    'RECOGNITION_FAILED': 'Face recognition failed. Please try again',
    'DATABASE_ERROR': 'Database operation failed',
    'FILE_UPLOAD_ERROR': 'Failed to upload file',
    'INVALID_FILE_TYPE': 'Invalid file type. Please upload PNG, JPG, or JPEG files',
    'FILE_TOO_LARGE': 'File size too large. Maximum size is 10MB',
}

# Success Messages
SUCCESS_MESSAGES: Dict[str, str] = {
    'LOGIN_SUCCESS': 'Login successful!',
    'LOGOUT_SUCCESS': 'Logged out successfully',
    'SIGNUP_SUCCESS': 'Account created successfully',
    'STUDENT_ADDED': 'Student registered successfully',
    'STUDENT_DELETED': 'Student removed successfully',
    'ATTENDANCE_MARKED': 'Attendance marked successfully',
    'PASSWORD_RESET': 'Password reset successful',
    'PROFILE_UPDATED': 'Profile updated successfully',
    'DATA_EXPORTED': 'Data exported successfully',
}

# Theme Constants
THEME_CONFIG = {
    'light': {
        'primary_color': '#1e40af',
        'background_color': '#ffffff',
        'secondary_color': '#f8fafc',
        'text_color': '#0f172a',
    },
    'dark': {
        'primary_color': '#3b82f6',
        'background_color': '#0f172a',
        'secondary_color': '#1e293b',
        'text_color': '#f8fafc',
    }
}

# Chart Colors
CHART_COLORS = [
    '#1e40af', '#3b82f6', '#60a5fa', '#93c5fd',
    '#10b981', '#34d399', '#6ee7b7', '#a7f3d0',
    '#f59e0b', '#fbbf24', '#fcd34d', '#fde68a',
    '#ef4444', '#f87171', '#fca5a5', '#fecaca',
]

# Export Formats
EXPORT_FORMATS = {
    'CSV': 'text/csv',
    'EXCEL': 'application/vnd.ms-excel',
    'PDF': 'application/pdf',
    'JSON': 'application/json',
}

# Date Formats
DATE_FORMATS = {
    'DISPLAY': '%B %d, %Y',          # January 01, 2025
    'SHORT': '%m/%d/%Y',             # 01/01/2025
    'ISO': '%Y-%m-%d',               # 2025-01-01
    'TIMESTAMP': '%Y-%m-%d %H:%M:%S', # 2025-01-01 10:30:45
    'TIME_12HR': '%I:%M:%S %p',      # 10:30:45 AM
    'TIME_24HR': '%H:%M:%S',         # 10:30:45
}

# API Response Codes
class ResponseCode:
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_ERROR = 500

# Logging Levels
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50,
}

# Regular Expressions
REGEX_PATTERNS = {
    'EMAIL': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'PHONE': r'^[\+]?[1-9][\d]{0,15}$',
    'USERNAME': r'^[a-zA-Z0-9_]{3,30}$',
    'ROLL_NUMBER': r'^[A-Z0-9]{6,20}$',
    'NAME': r'^[a-zA-Z\s\'\.]{2,100}$',
}

# Cache Keys
CACHE_KEYS = {
    'STUDENT_LIST': 'students_list',
    'USER_LIST': 'users_list',
    'ATTENDANCE_STATS': 'attendance_stats',
    'FACE_EMBEDDINGS': 'face_embeddings',
    'ANALYTICS_DATA': 'analytics_data',
}

# Notification Types
class NotificationType:
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'

# Default Values
DEFAULTS = {
    'PAGINATION_SIZE': 20,
    'RECOGNITION_THRESHOLD': 0.6,
    'SESSION_TIMEOUT_HOURS': 24,
    'MAX_LOGIN_ATTEMPTS': 5,
    'PASSWORD_MIN_LENGTH': 6,
    'PHOTO_MAX_SIZE_MB': 10,
    'ANALYTICS_DAYS': 30,
}
