"""
Login page component — auth navigation, password reset, and session integration.
"""
import streamlit as st
import time
import logging
from typing import Optional, Dict, Tuple

from auth.authentication import AuthenticationService
from auth.session_manager import SessionManager
from ui.components.forms import LoginForm, SignupForm
from ui.components.theme_toggle import theme_toggle
from ui.theme import PremiumTheme

logger = logging.getLogger(__name__)

AUTH_NAV_KEY = "login_auth_navigation"


class LoginPage:
    """Login page component"""

    def __init__(self):
        self.auth_service = AuthenticationService()
        self.session_manager = SessionManager()

    def render(self):
        """Render complete login page"""
        # Theme toggle
        _, _, top_right = st.columns([6, 2, 2])
        with top_right:
            theme_toggle.render_toggle_button()

        # Premium login card
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Premium branding header
            st.markdown("""
            <div style="text-align: center; margin-bottom: 2rem;">
                <div style="font-size: 4rem; margin-bottom: 0.5rem;">🎓</div>
                <h1 style="color: #4F46E5; margin: 0; font-size: 2.5rem; font-weight: 700;">Smart Face Attendance</h1>
                <p style="color: #64748B; margin: 0.75rem 0 0 0; font-size: 1.1rem;">Enterprise Management System</p>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("totp_challenge"):
                self._render_totp_challenge()
                return

            # Prominent password reset step (after user requests token)
            if st.session_state.get("show_password_reset"):
                self._render_password_reset_card()
                st.markdown("---")

            # Navigation: radio allows switching to Forgot Password from LoginForm button
            options = ["Login", "Sign Up", "Forgot Password"]
            
            # Initialize session state if not exists
            if AUTH_NAV_KEY not in st.session_state:
                st.session_state[AUTH_NAV_KEY] = "Login"

            if st.session_state.pop("goto_forgot_password", False):
                st.session_state[AUTH_NAV_KEY] = "Forgot Password"

            # Premium tab navigation
            nav = st.segmented_control(
                "Account",
                options,
                key=AUTH_NAV_KEY,
                label_visibility="collapsed",
            )

            if nav == "Login":
                self._render_login_tab()
            elif nav == "Sign Up":
                self._render_signup_tab()
            else:
                self._render_forgot_password_tab()

    def _render_totp_challenge(self):
        """Second step: TOTP for admins with 2FA enabled."""
        with st.container():
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            ch = st.session_state.get("totp_challenge") or {}
            em = ch.get("email", "")
            st.markdown("#### 🔐 Authenticator Code")
            st.caption(f"Account **{em}** — open your authenticator app and enter the 6-digit code.")
            with st.form("totp_form"):
                code = st.text_input("Code", max_chars=8, placeholder="123456")
                verify = st.form_submit_button("Verify and continue", use_container_width=True)
                cancel = st.form_submit_button("Cancel", type="secondary", use_container_width=True)
            if cancel:
                st.session_state.pop("totp_challenge", None)
                st.rerun()
            elif verify:
                if not (code and code.strip()):
                    st.error("Enter the 6-digit code from your app.")
                else:
                    ok, msg, user_data = self.auth_service.complete_totp_login(em, code.strip())
                    if ok and user_data:
                        st.session_state.pop("totp_challenge", None)
                        self.session_manager.login_user(user_data)
                        st.success("Signed in.")
                        time.sleep(0.4)
                        st.rerun()
                    else:
                        st.error(msg or "Invalid code.")
            st.markdown('</div>', unsafe_allow_html=True)

    def _render_login_tab(self):
        """Render login tab"""
        with st.container():
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            email, password, submitted = LoginForm.render()

            if submitted:
                self._handle_login(email, password)
            st.markdown('</div>', unsafe_allow_html=True)

    def _render_signup_tab(self):
        """Render signup tab"""
        with st.container():
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("### ✨ Create Account")
            user_data, submitted = SignupForm.render()

            if submitted and user_data:
                self._handle_signup(user_data)
            st.markdown('</div>', unsafe_allow_html=True)

    def _render_forgot_password_tab(self):
        """Render forgot password tab"""
        with st.container():
            st.markdown('<div class="premium-card">', unsafe_allow_html=True)
            st.markdown("### 🔑 Reset Password")
            self._render_forgot_password_form()
            st.markdown('</div>', unsafe_allow_html=True)

    def _render_forgot_password_form(self):
        """Request reset token"""
        st.caption("We will email a reset link if SMTP is configured; otherwise a one-time token appears on screen.")

        with st.form("forgot_password_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="you@example.com")
            reset_btn = st.form_submit_button("Send reset instructions", use_container_width=True)

            if reset_btn:
                if not email or not email.strip():
                    st.error("Enter your email address.")
                else:
                    self._handle_password_reset_request(email.strip())

    def _render_password_reset_card(self):
        """Password reset form (token + new password) — shown at top when active"""
        st.markdown("#### Set new password")
        with st.form("password_reset_form"):
            st.caption(f"Resetting password for: **{st.session_state.get('reset_email', '')}**")

            reset_token = st.text_input(
                "Reset token",
                value=st.session_state.get("reset_token", ""),
                help="Paste the token from the message or email",
            )

            new_password = st.text_input(
                "New password",
                type="password",
                placeholder="Min. 6 characters",
            )

            confirm_new_password = st.text_input(
                "Confirm new password",
                type="password",
            )

            col1, col2 = st.columns(2)
            with col1:
                reset_password_btn = st.form_submit_button("Update password", use_container_width=True)
            with col2:
                cancel_btn = st.form_submit_button("Cancel", use_container_width=True, type="secondary")

            if reset_password_btn:
                self._handle_password_reset(reset_token, new_password, confirm_new_password)

            if cancel_btn:
                self._clear_password_reset_session()
                st.rerun()

    def _handle_login(self, email: str, password: str):
        """Handle login submission"""
        if not email or not password:
            st.error("Enter both email and password.")
            return

        with st.spinner("Signing in…"):
            success, message, user_data = self.auth_service.login_user(email.strip(), password)

            if success and user_data:
                if user_data.get("pending_totp"):
                    st.session_state["totp_challenge"] = {"email": user_data["email"]}
                    st.rerun()
                    return
                self.session_manager.login_user(user_data)
                st.success("Signed in successfully.")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(message or "Invalid email or password.")

    def _handle_signup(self, user_data: Dict):
        """Handle signup submission"""
        with st.spinner("Creating account…"):
            success, message = self.auth_service.signup_user(
                user_data["username"],
                user_data["email"],
                user_data["password"],
            )

            if success:
                st.success(f"{message} You can sign in now.")
            else:
                st.error(message)

    def _handle_password_reset_request(self, email: str):
        """Handle password reset request"""
        with st.spinner("Processing…"):
            success, msg, token = self.auth_service.initiate_password_reset(email)

            if not success:
                st.error(msg)
                return

            if token:
                st.success(msg)
                st.session_state["reset_token"] = token
                st.session_state["reset_email"] = email.strip().lower()
                st.session_state["show_password_reset"] = True
                st.info("Use **Set new password** above with the token you received.")
                st.rerun()
            else:
                # Email not registered (we do not reveal); generic message
                st.success(msg)

    def _handle_password_reset(self, token: str, new_password: str, confirm_password: str):
        """Reset password with token"""
        token = (token or "").strip()
        if not token or not new_password or not confirm_password:
            st.error("Fill in token, new password, and confirmation.")
            return

        if new_password != confirm_password:
            st.error("Passwords do not match.")
            return

        email = st.session_state.get("reset_email", "")
        if not email:
            st.error("Session lost. Request a new reset from **Forgot Password**.")
            return

        with st.spinner("Updating password…"):
            success, message = self.auth_service.reset_password(email, token, new_password)

            if success:
                st.success("Password updated. You can sign in with your new password.")
                self._clear_password_reset_session()
                st.session_state[AUTH_NAV_KEY] = "Login"
                time.sleep(1.0)
                st.rerun()
            else:
                st.error(message)

    def _clear_password_reset_session(self):
        for key in ("reset_token", "reset_email", "show_password_reset"):
            st.session_state.pop(key, None)
