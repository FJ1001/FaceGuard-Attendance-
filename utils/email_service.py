"""
Email service for sending notifications
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple

from config.settings import get_config_value

logger = logging.getLogger(__name__)


class EmailService:
    """Handle email sending operations"""
    
    def __init__(self):
        self.smtp_enabled = self._get_boolean_config('SMTP_ENABLED', False)
        self.smtp_server = get_config_value('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(get_config_value('SMTP_PORT', '587'))
        self.smtp_use_tls = self._get_boolean_config('SMTP_USE_TLS', True)
        self.smtp_username = get_config_value('SMTP_USERNAME', '')
        self.smtp_password = get_config_value('SMTP_PASSWORD', '')
        self.from_email = get_config_value('FROM_EMAIL', self.smtp_username)
    
    def _get_boolean_config(self, key: str, default: bool) -> bool:
        """Get boolean configuration value"""
        value = get_config_value(key, str(default))
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', 'on']
        return default
    
    def send_password_reset_email(self, email: str, reset_token: str) -> Tuple[bool, str]:
        """Send password reset email"""
        try:
            if not self.smtp_enabled:
                logger.info(f"📧 SMTP disabled. Reset token for {email}: {reset_token}")
                return True, f"🔑 Your reset token: {reset_token}"
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = "🔐 Password Reset - Smart Attendance System"
            
            # Email body
            body = f"""
Hello,

You requested a password reset for your Smart Attendance System account.

Your reset token is: {reset_token}

Please use this token to reset your password within 1 hour.

If you didn't request this reset, please ignore this email.

Best regards,
Smart Attendance System Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email (timeout avoids hanging UI)
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=25)
            if self.smtp_use_tls:
                server.starttls()
            
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"📧 Password reset email sent to: {email}")
            return True, "📧 Reset email sent successfully! Check your inbox."
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {email}: {e}")
            # Fallback: show token when email fails
            return True, f"📧 Email failed. Your reset token: {reset_token}"
