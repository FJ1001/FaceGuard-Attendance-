"""
User service for authentication and user management
Bridges the gap between UI and user repository
"""

import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from database.user_repository import UserRepository
import hashlib

logger = logging.getLogger(__name__)

class UserService:
    """Service layer for user management operations"""
    
    def __init__(self):
        self.user_repository = UserRepository()
    
    def create_user(self, email: str, password: str, username: str = None, role: str = 'user') -> Tuple[bool, str]:
        """Create new user with validation"""
        try:
            # Input validation
            if not email or not password:
                return False, "Email and password are required"
            
            if not self._is_valid_email(email):
                return False, "Invalid email format"
            
            if len(password) < 6:
                return False, "Password must be at least 6 characters long"
            
            # Generate username if not provided
            if not username:
                username = email.split('@')[0]
            
            # Hash password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Create user via repository
            success, message = self.user_repository.create_user(
                username=username,
                email=email.lower(),
                password_hash=password_hash,
                role=role
            )
            
            if success:
                logger.info(f"User created successfully: {email} ({role})")
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"Error creating user: {str(e)}"
    
    def authenticate_user(self, email: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """Authenticate user credentials"""
        try:
            if not email or not password:
                return False, None, "Email and password are required"
            
            # Get user from repository
            user = self.user_repository.get_user_by_email(email.lower())
            if not user:
                return False, None, "Invalid email or password"
            
            # Verify password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user.get('password_hash') != password_hash:
                return False, None, "Invalid email or password"
            
            # Update last login
            self.user_repository.update_last_login(email.lower())
            
            # Remove sensitive data before returning
            safe_user = {
                'id': user['id'],
                'email': user['email'],
                'username': user['username'],
                'role': user['role'],
                'created_at': user['created_at']
            }
            
            logger.info(f"User authenticated successfully: {email}")
            return True, safe_user, "Login successful"
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return False, None, "Authentication failed"
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (admin only)"""
        try:
            return self.user_repository.get_all_users()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """Delete user by ID"""
        try:
            return self.user_repository.delete_user(user_id)
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False, f"Error deleting user: {str(e)}"
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            return self.user_repository.get_user_by_email(email.lower())
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def update_user_password(self, email: str, new_password: str) -> Tuple[bool, str]:
        """Update user password"""
        try:
            if len(new_password) < 6:
                return False, "Password must be at least 6 characters long"
            
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            success = self.user_repository.change_password(email.lower(), password_hash)
            
            if success:
                logger.info(f"Password updated for user: {email}")
                return True, "Password updated successfully"
            else:
                return False, "Failed to update password"
                
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return False, f"Error updating password: {str(e)}"
    
    def initiate_password_reset(self, email: str) -> Tuple[bool, str, Optional[str]]:
        """Initiate password reset process"""
        try:
            user = self.user_repository.get_user_by_email(email.lower())
            if not user:
                # Don't reveal if email exists
                return True, "If the email exists, reset instructions have been sent", None
            
            # Generate reset token (in production, use cryptographically secure token)
            import secrets
            reset_token = secrets.token_urlsafe(32)
            
            # Store reset token (implement in repository)
            # For now, just return the token for demo purposes
            logger.info(f"Password reset initiated for: {email}")
            return True, "Reset token generated", reset_token
            
        except Exception as e:
            logger.error(f"Error initiating password reset: {e}")
            return False, "Error processing request", None
    
    def reset_password(self, email: str, token: str, new_password: str) -> Tuple[bool, str]:
        """Reset password using token"""
        try:
            # In a real implementation, verify the token
            # For demo purposes, just update the password
            return self.update_user_password(email, new_password)
            
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False, f"Error resetting password: {str(e)}"
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

# Global service instance
user_service = UserService()

# Convenience functions for backward compatibility
def signup_user(email: str, password: str, role: str = 'user') -> Tuple[bool, str, Optional[Dict]]:
    """Create new user account"""
    success, message = user_service.create_user(email, password, role=role)
    if success:
        user = user_service.get_user_by_email(email)
        return success, message, user
    return success, message, None

def login_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """Authenticate user login"""
    return user_service.authenticate_user(email, password)

def get_all_users() -> List[Dict]:
    """Get all users"""
    return user_service.get_all_users()

def delete_user(user_id: int) -> Tuple[bool, str]:
    """Delete user"""
    return user_service.delete_user(user_id)

def initiate_password_reset(email: str) -> Tuple[bool, str, Optional[str]]:
    """Initiate password reset"""
    return user_service.initiate_password_reset(email)

def reset_password(email: str, token: str, new_password: str) -> Tuple[bool, str]:
    """Reset password"""
    return user_service.reset_password(email, token, new_password)
