"""
Authentication service
Extracted from auth.py authentication functions
"""
import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, List  # Added missing imports

from database.user_repository import UserRepository
from database.rate_limit_repository import (
    count_password_reset_attempts,
    record_password_reset_attempt,
)
from auth.validators import validate_email, validate_password, validate_username, sanitize_input
from auth.password_hashing import (
    hash_password as _hash_password_impl,
    verify_password as _verify_password_impl,
    is_legacy_sha256_hash,
)


logger = logging.getLogger(__name__)


def _token_expiry_hours() -> int:
    try:
        return int(os.getenv("TOKEN_EXPIRY_HOURS", "1"))
    except ValueError:
        return 1


def _password_reset_max_per_hour() -> int:
    try:
        return int(os.getenv("PASSWORD_RESET_MAX_PER_HOUR", "5"))
    except ValueError:
        return 5


def _admin_2fa_enabled() -> bool:
    return os.getenv("ENABLE_ADMIN_2FA", "false").lower() in ("1", "true", "yes")


def _audit(action: str, **kwargs) -> None:
    """Lazy import so auth never participates in import cycles with audit/DB."""
    try:
        from services.audit_service import log as audit_write

        audit_write(action, **kwargs)
    except Exception:
        pass


class AuthenticationService:
    """Handle user authentication operations"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt (new accounts and password updates)."""
        return _hash_password_impl(password)

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password (bcrypt or legacy SHA-256)."""
        return _verify_password_impl(password, stored_hash)
    
    def generate_secure_token(self) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(32)
    
    def signup_user(self, username: str, email: str, password: str, 
                   role: str = 'user') -> Tuple[bool, str]:
        """Register new user"""
        try:
            # Sanitize inputs
            username = sanitize_input(username)
            email = sanitize_input(email).lower()
            role = sanitize_input(role).lower()
            
            # Validate inputs
            if not validate_email(email):
                return False, "Invalid email format"
            
            username_valid, username_msg = validate_username(username)
            if not username_valid:
                return False, username_msg
            
            password_valid, password_msg = validate_password(password)
            if not password_valid:
                return False, password_msg
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user in database
            success, message = self.user_repo.create_user(username, email, password_hash, role)
            
            if success:
                logger.info(f"New user registered: {email}")
                _audit("user_signup", actor_email=email, detail={"username": username, "role": role})
            else:
                logger.warning(f"User registration failed: {email} - {message}")
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error in user signup: {e}")
            return False, f"Registration failed: {str(e)}"
    
    def login_user(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """Authenticate user login"""
        try:
            # Sanitize inputs
            email = sanitize_input(email).lower()
            
            # Validate email format
            if not validate_email(email):
                return False, "Invalid email format", None
            
            # Get user from database
            user = self.user_repo.get_user_by_email(email)
            if not user:
                logger.warning(f"Login attempt with non-existent email: {email}")
                _audit("login_failed", actor_email=email, detail={"reason": "unknown_user"})
                return False, "Invalid email or password", None
            
            # Verify password
            if not self.verify_password(password, user['password_hash']):
                logger.warning(f"Failed login attempt for: {email}")
                _audit("login_failed", actor_email=email, detail={"reason": "bad_password"})
                return False, "Invalid email or password", None

            # Upgrade legacy SHA-256 hash to bcrypt on successful login
            if is_legacy_sha256_hash(user["password_hash"]):
                try:
                    new_hash = self.hash_password(password)
                    self.user_repo.update_password(email, new_hash)
                    logger.info("Password hash upgraded to bcrypt for user: %s", email)
                except Exception as exc:
                    logger.warning("Could not upgrade password hash for %s: %s", email, exc)

            if (
                _admin_2fa_enabled()
                and user.get("role") == "admin"
                and user.get("totp_enabled")
                and user.get("totp_secret")
            ):
                user_info = {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": user["role"],
                    "created_at": user["created_at"],
                    "last_login": user["last_login"],
                    "pending_totp": True,
                }
                _audit("login_totp_challenge", actor_email=email)
                logger.info("Awaiting TOTP for admin: %s", email)
                return True, "Enter your authenticator code.", user_info

            self.user_repo.update_last_login(email)

            user_info = {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "created_at": user["created_at"],
                "last_login": user["last_login"],
            }

            _audit("login_success", actor_email=email, detail={"method": "password"})
            logger.info(f"Successful login: {email}")
            return True, "Login successful", user_info

        except Exception as e:
            logger.error(f"Error in user login: {e}")
            return False, f"Login failed: {str(e)}", None

    def complete_totp_login(self, email: str, code: str) -> Tuple[bool, str, Optional[Dict]]:
        """Complete admin login after TOTP verification."""
        try:
            email = sanitize_input(email).lower()
            if not validate_email(email) or not code:
                return False, "Invalid input", None
            user = self.user_repo.get_user_by_email(email)
            if not user or not user.get("totp_secret"):
                return False, "Invalid session", None
            import pyotp

            if not pyotp.TOTP(user["totp_secret"]).verify(code.strip(), valid_window=1):
                _audit("totp_failed", actor_email=email)
                return False, "Invalid authenticator code", None

            self.user_repo.update_last_login(email)
            user_info = {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "created_at": user["created_at"],
                "last_login": user["last_login"],
            }
            _audit("login_success", actor_email=email, detail={"method": "totp"})
            return True, "Login successful", user_info
        except Exception as e:
            logger.error("complete_totp_login: %s", e)
            return False, "Verification failed", None

    def generate_admin_totp_secret(self, email: str) -> Tuple[bool, str, Optional[str]]:
        """Create TOTP secret + provisioning URI (enable after confirm_admin_totp)."""
        try:
            import pyotp

            email = sanitize_input(email).lower()
            user = self.user_repo.get_user_by_email(email)
            if not user or user.get("role") != "admin":
                return False, "", None
            secret = pyotp.random_base32()
            self.user_repo.set_totp_secret(email, secret)
            self.user_repo.set_totp_enabled(email, False)
            uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=email, issuer_name="Smart Attendance"
            )
            _audit("totp_secret_generated", actor_email=email)
            return True, secret, uri
        except Exception as e:
            logger.error("generate_admin_totp_secret: %s", e)
            return False, "", None

    def confirm_admin_totp(self, email: str, code: str) -> Tuple[bool, str]:
        try:
            import pyotp

            email = sanitize_input(email).lower()
            user = self.user_repo.get_user_by_email(email)
            if not user or not user.get("totp_secret"):
                return False, "Generate a secret first."
            if not pyotp.TOTP(user["totp_secret"]).verify(code.strip(), valid_window=1):
                return False, "Invalid code — check device time sync."
            self.user_repo.set_totp_enabled(email, True)
            _audit("totp_enabled", actor_email=email)
            return True, "Two-factor authentication is now enabled for this account."
        except Exception as e:
            logger.error("confirm_admin_totp: %s", e)
            return False, str(e)

    def disable_admin_totp(self, email: str, password: str) -> Tuple[bool, str]:
        try:
            email = sanitize_input(email).lower()
            user = self.user_repo.get_user_by_email(email)
            if not user:
                return False, "User not found"
            if not self.verify_password(password, user["password_hash"]):
                return False, "Incorrect password"
            self.user_repo.set_totp_secret(email, "")
            self.user_repo.set_totp_enabled(email, False)
            _audit("totp_disabled", actor_email=email)
            return True, "Two-factor authentication disabled."
        except Exception as e:
            logger.error("disable_admin_totp: %s", e)
            return False, str(e)
    
    def initiate_password_reset(self, email: str) -> Tuple[bool, str, Optional[str]]:
        """Initiate password reset process"""
        try:
            email = sanitize_input(email).lower()
            
            if not validate_email(email):
                return False, "Invalid email format", None

            if count_password_reset_attempts(email) >= _password_reset_max_per_hour():
                _audit("password_reset_rate_limited", actor_email=email)
                return (
                    False,
                    "Too many reset attempts for this email. Try again in about an hour.",
                    None,
                )

            record_password_reset_attempt(email)
            
            # Check if user exists
            user = self.user_repo.get_user_by_email(email)
            if not user:
                _audit("password_reset_unknown_email", actor_email=email)
                return True, "If the email exists, a reset link will be sent", None
            
            # Generate reset token
            reset_token = self.generate_secure_token()
            expires = datetime.now() + timedelta(hours=_token_expiry_hours())
            
            # Store token in database
            success = self.user_repo.store_reset_token(email, reset_token, expires)
            
            if success:
                # Send email with reset token
                try:
                    from utils.email_service import EmailService
                    email_service = EmailService()
                    email_sent, email_message = email_service.send_password_reset_email(email, reset_token)
                    
                    logger.info(f"Password reset initiated for: {email}")
                    _audit("password_reset_issued", actor_email=email)
                    return True, email_message, reset_token
                    
                except Exception as email_error:
                    logger.error(f"Email service error: {email_error}")
                    _audit("password_reset_issued", actor_email=email)
                    return True, f"🔑 Reset token generated: {reset_token}", reset_token
            else:
                return False, "Failed to generate reset token", None
                
        except Exception as e:
            logger.error(f"Error initiating password reset: {e}")
            return False, f"Password reset failed: {str(e)}", None
    
    def reset_password(self, email: str, token: str, new_password: str) -> Tuple[bool, str]:
        """Reset user password with token"""
        try:
            email = sanitize_input(email).lower()
            
            # Validate inputs
            if not validate_email(email):
                return False, "Invalid email format"
            
            password_valid, password_msg = validate_password(new_password)
            if not password_valid:
                return False, password_msg
            
            # Verify reset token
            if not self.user_repo.verify_reset_token(email, token):
                logger.warning(f"Invalid or expired reset token for: {email}")
                return False, "Invalid or expired reset token"
            
            # Hash new password
            new_password_hash = self.hash_password(new_password)
            
            # Update password
            success = self.user_repo.update_password(email, new_password_hash)
            
            if success:
                logger.info(f"Password reset successful for: {email}")
                _audit("password_reset_complete", actor_email=email)
                return True, "Password reset successful"
            else:
                return False, "Failed to update password"
                
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False, f"Password reset failed: {str(e)}"
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (admin only)"""
        return self.user_repo.get_all_users()
    
    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """Delete user (admin only)"""
        return self.user_repo.delete_user(user_id)


# Standalone functions for backward compatibility
def hash_password(password: str) -> str:
    """Standalone hash password function"""
    auth_service = AuthenticationService()
    return auth_service.hash_password(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """Standalone verify password function"""
    auth_service = AuthenticationService()
    return auth_service.verify_password(password, stored_hash)


def generate_secure_token() -> str:
    """Standalone token generation function"""
    auth_service = AuthenticationService()
    return auth_service.generate_secure_token()
