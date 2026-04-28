"""
Session management for Streamlit
Handles user sessions and authentication state
"""
import streamlit as st
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from config.settings import SESSION_KEYS

logger = logging.getLogger(__name__)

class SessionManager:
    """Manage user sessions in Streamlit"""
    
    def __init__(self):
        self.session_keys = SESSION_KEYS
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize session state variables"""
        for key in self.session_keys.values():
            if key not in st.session_state:
                st.session_state[key] = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return st.session_state.get(self.session_keys['LOGIN_STATUS'], False)
    
    def login_user(self, user_info: Dict[str, Any]) -> bool:
        """Login user and set session variables"""
        try:
            st.session_state[self.session_keys['LOGIN_STATUS']] = True
            st.session_state[self.session_keys['USERNAME']] = user_info['username']
            st.session_state[self.session_keys['USER_EMAIL']] = user_info['email']
            st.session_state[self.session_keys['USER_ROLE']] = user_info['role']
            st.session_state['login_time'] = datetime.now()
            
            logger.info(f"User logged in: {user_info['email']}")
            return True
        except Exception as e:
            logger.error(f"Error logging in user: {e}")
            return False
    
    def logout_user(self):
        """Logout user and clear session"""
        try:
            user_email = st.session_state.get(self.session_keys['USER_EMAIL'])
            if user_email:
                try:
                    from services.audit_service import log as audit_log

                    audit_log("logout", actor_email=user_email)
                except Exception:
                    pass

            # Clear all session variables
            for key in self.session_keys.values():
                st.session_state[key] = None
            
            # Clear additional session variables
            session_vars_to_clear = [
                'login_time', 'show_signup', 'show_forgot_password',
                'reset_token', 'reset_email', 'show_password_reset', 'goto_forgot_password',
                'login_auth_navigation', 'totp_challenge',
            ]
            
            for var in session_vars_to_clear:
                if var in st.session_state:
                    del st.session_state[var]
            
            logger.info(f"User logged out: {user_email}")
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        if not self.is_authenticated():
            return None
        
        return {
            'username': st.session_state.get(self.session_keys['USERNAME']),
            'email': st.session_state.get(self.session_keys['USER_EMAIL']),
            'role': st.session_state.get(self.session_keys['USER_ROLE']),
            'login_time': st.session_state.get('login_time')
        }
    
    def is_admin(self) -> bool:
        """Check if current user is admin"""
        return (self.is_authenticated() and 
                st.session_state.get(self.session_keys['USER_ROLE']) == 'admin')
    
    def get_user_role(self) -> Optional[str]:
        """Get current user role"""
        return st.session_state.get(self.session_keys['USER_ROLE'])
    
    def check_session_timeout(self, timeout_hours: int = 24) -> bool:
        """Check if session has timed out"""
        try:
            login_time = st.session_state.get('login_time')
            if not login_time:
                return True
            
            if datetime.now() - login_time > timedelta(hours=timeout_hours):
                self.logout_user()
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking session timeout: {e}")
            return True
    
    def refresh_session(self):
        """Refresh session timestamp"""
        if self.is_authenticated():
            st.session_state['login_time'] = datetime.now()
    
    def set_session_variable(self, key: str, value: Any):
        """Set a session variable"""
        st.session_state[key] = value
    
    def get_session_variable(self, key: str, default: Any = None) -> Any:
        """Get a session variable"""
        return st.session_state.get(key, default)
    
    def clear_session_variable(self, key: str):
        """Clear a specific session variable"""
        if key in st.session_state:
            del st.session_state[key]
