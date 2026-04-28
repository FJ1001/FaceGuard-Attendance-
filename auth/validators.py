"""
Authentication validators
Extracted from auth.py validation functions
"""
import os
import re
import logging
from typing import Tuple  # Added missing import

try:
    MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "6"))
except ValueError:
    MIN_PASSWORD_LENGTH = 6
EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

logger = logging.getLogger(__name__)

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    return re.match(EMAIL_PATTERN, email.strip()) is not None

def validate_password(password: str) -> Tuple[bool, str]:
    """Enhanced password validation"""
    if not password or not isinstance(password, str):
        return False, "Password is required"
    
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    
    # Check for at least one letter
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    
    return True, "Password is valid"

def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username format"""
    if not username or not isinstance(username, str):
        return False, "Username is required"
    
    username = username.strip()
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 30:
        return False, "Username must be less than 30 characters"
    
    # Only allow alphanumeric and underscore
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, "Username is valid"

def validate_user_role(role: str) -> bool:
    """Validate user role"""
    valid_roles = ['user', 'admin']
    return role in valid_roles

def sanitize_input(input_str: str) -> str:
    """Sanitize user input"""
    if not input_str:
        return ""
    
    # Strip whitespace
    sanitized = input_str.strip()
    
    # Remove any null bytes
    sanitized = sanitized.replace('\x00', '')
    
    return sanitized
