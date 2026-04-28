"""
Helper utility functions
Common utility functions used across the application
"""
import hashlib
import uuid
import re
import base64
import numpy as np
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import logging

from utils.constants import (
    REGEX_PATTERNS, DATE_FORMATS, ALLOWED_IMAGE_EXTENSIONS,
    ERROR_MESSAGES, SUCCESS_MESSAGES
)

logger = logging.getLogger(__name__)

def generate_unique_id() -> str:
    """Generate a unique identifier"""
    return str(uuid.uuid4())

def generate_short_id(length: int = 8) -> str:
    """Generate a short unique identifier"""
    return str(uuid.uuid4()).replace('-', '')[:length].upper()

def hash_string(text: str, salt: str = '') -> str:
    """Hash a string with optional salt"""
    return hashlib.sha256((text + salt).encode()).hexdigest()

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    return re.match(REGEX_PATTERNS['EMAIL'], email.strip()) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    if not phone or not isinstance(phone, str):
        return False
    return re.match(REGEX_PATTERNS['PHONE'], phone.strip()) is not None

def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username or not isinstance(username, str):
        return False
    return re.match(REGEX_PATTERNS['USERNAME'], username.strip()) is not None

def validate_roll_number(roll_number: str) -> bool:
    """Validate roll number format"""
    if not roll_number or not isinstance(roll_number, str):
        return False
    return re.match(REGEX_PATTERNS['ROLL_NUMBER'], roll_number.strip().upper()) is not None

def validate_name(name: str) -> bool:
    """Validate name format"""
    if not name or not isinstance(name, str):
        return False
    return re.match(REGEX_PATTERNS['NAME'], name.strip()) is not None

def sanitize_input(input_str: str) -> str:
    """Sanitize user input"""
    if not input_str or not isinstance(input_str, str):
        return ""
    
    # Strip whitespace and remove null bytes
    sanitized = input_str.strip().replace('\x00', '')
    
    # Remove any potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', sanitized)
    
    return sanitized

def format_date(date_obj: Union[date, datetime], format_key: str = 'DISPLAY') -> str:
    """Format date using predefined formats"""
    if not date_obj:
        return ""
    
    try:
        format_string = DATE_FORMATS.get(format_key, DATE_FORMATS['DISPLAY'])
        
        if isinstance(date_obj, str):
            # Try to parse string date
            try:
                date_obj = datetime.fromisoformat(date_obj)
            except:
                return date_obj
        
        return date_obj.strftime(format_string)
    except Exception as e:
        logger.warning(f"Date formatting error: {e}")
        return str(date_obj)

def parse_date(date_string: str, format_key: str = 'ISO') -> Optional[datetime]:
    """Parse date string to datetime object"""
    if not date_string:
        return None
    
    try:
        format_string = DATE_FORMATS.get(format_key, DATE_FORMATS['ISO'])
        return datetime.strptime(date_string, format_string)
    except Exception as e:
        logger.warning(f"Date parsing error: {e}")
        return None

def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def get_time_difference(start_time: datetime, end_time: datetime = None) -> str:
    """Get human-readable time difference"""
    if not start_time:
        return "Unknown"
    
    if not end_time:
        end_time = datetime.now()
    
    try:
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
        
        diff = end_time - start_time
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    except Exception as e:
        logger.warning(f"Time difference calculation error: {e}")
        return "Unknown"

def validate_file_extension(filename: str) -> bool:
    """Validate file extension"""
    if not filename:
        return False
    
    file_path = Path(filename)
    return file_path.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS

def get_file_size_mb(file_size_bytes: int) -> float:
    """Convert file size from bytes to MB"""
    return file_size_bytes / (1024 * 1024)

def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate string to maximum length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def encode_numpy_array(arr: np.ndarray) -> str:
    """Encode numpy array to base64 string"""
    try:
        return base64.b64encode(arr.tobytes()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding numpy array: {e}")
        return ""

def decode_numpy_array(encoded_str: str, dtype=np.float32, shape: Optional[Tuple] = None) -> Optional[np.ndarray]:
    """Decode base64 string to numpy array"""
    try:
        array_bytes = base64.b64decode(encoded_str)
        arr = np.frombuffer(array_bytes, dtype=dtype)
        
        if shape:
            arr = arr.reshape(shape)
        
        return arr
    except Exception as e:
        logger.error(f"Error decoding numpy array: {e}")
        return None

def calculate_percentage(part: Union[int, float], total: Union[int, float]) -> float:
    """Calculate percentage with safety checks"""
    if not total or total == 0:
        return 0.0
    
    return round((part / total) * 100, 2)

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def safe_divide(numerator: Union[int, float], denominator: Union[int, float], default: float = 0.0) -> float:
    """Safe division with default value"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default

def get_nested_value(data: Dict, keys: str, default: Any = None, separator: str = '.') -> Any:
    """Get nested dictionary value using dot notation"""
    try:
        key_list = keys.split(separator)
        value = data
        
        for key in key_list:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    except:
        return default

def set_nested_value(data: Dict, keys: str, value: Any, separator: str = '.') -> Dict:
    """Set nested dictionary value using dot notation"""
    key_list = keys.split(separator)
    current = data
    
    for key in key_list[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[key_list[-1]] = value
    return data

def is_business_day(date_obj: date) -> bool:
    """Check if date is a business day (Monday-Friday)"""
    return date_obj.weekday() < 5

def get_next_business_day(date_obj: date) -> date:
    """Get next business day"""
    next_day = date_obj + timedelta(days=1)
    
    while not is_business_day(next_day):
        next_day += timedelta(days=1)
    
    return next_day

def generate_color_palette(num_colors: int) -> List[str]:
    """Generate a color palette with specified number of colors"""
    from utils.constants import CHART_COLORS
    
    if num_colors <= len(CHART_COLORS):
        return CHART_COLORS[:num_colors]
    
    # Generate additional colors if needed
    colors = CHART_COLORS.copy()
    
    for i in range(len(CHART_COLORS), num_colors):
        # Generate colors using HSL
        hue = (i * 137.508) % 360  # Golden angle approximation
        color = f"hsl({hue}, 70%, 50%)"
        colors.append(color)
    
    return colors

def mask_sensitive_data(data: str, visible_chars: int = 4, mask_char: str = '*') -> str:
    """Mask sensitive data showing only first few characters"""
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ""
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)

def clean_filename(filename: str) -> str:
    """Clean filename to be filesystem safe"""
    if not filename:
        return "unnamed"
    
    # Remove or replace invalid characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple underscores
    cleaned = re.sub(r'_+', '_', cleaned)
    
    # Trim and remove leading/trailing dots
    cleaned = cleaned.strip(' ._')
    
    return cleaned or "unnamed"

def get_error_message(error_key: str, default: str = "An error occurred") -> str:
    """Get error message by key"""
    return ERROR_MESSAGES.get(error_key, default)

def get_success_message(success_key: str, default: str = "Operation successful") -> str:
    """Get success message by key"""
    return SUCCESS_MESSAGES.get(success_key, default)

def retry_on_failure(func, max_attempts: int = 3, delay: float = 1.0, exceptions: Tuple = (Exception,)):
    """Retry function on failure"""
    import time
    
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            if attempt == max_attempts - 1:
                raise e
            
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    
    return None
