"""
System health, backups, audit log preview, and admin TOTP setup.
"""

from __future__ import annotations

import io
import logging
from typing import Any, Dict

import streamlit as st

from auth.authentication import AuthenticationService
from auth.session_manager import SessionManager
from config.settings import BASE_DIR, DB_FILE, ENABLE_ADMIN_2FA, get_config_value
from database.audit_repository import list_recent_audit
from ui.components.layout import render_page_header, section_title
from utils.backup_manager import BackupManager
from utils.health_check import check_model_files, database_status, disk_free_gb

logger = logging.getLogger(__name__)


class HealthPage:
    def render(self):
        render_page_header(
            title="System health",
            subtitle="Database, disk, models, backups, security, and audit trail.",
            icon="🩺",
        )

        # --- Status cards
        db = database_status()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Database", "OK" if db["exists"] else "Missing", f"{db['size_mb']} MB")
        with col2:
            st.metric("Free disk (project drive)", f"{disk_free_gb(BASE_DIR)} GB")
        with col3:
            smtp = str(get_config_value("SMTP_ENABLED", "false")).lower() in ("1", "true", "yes")
            st.metric("SMTP mail", "On" if smtp else "Off")

        section_title("Paths", icon="📁")
        st.code(str(DB_FILE), language="text")

        section_title("Model / artifact checks", icon="🧠")
        for row in check_model_files():
            icon = "✅" if row.get("exists") else "❌"
            extra = f" ({row.get('size_mb')} MB)" if row.get("size_mb") is not None else ""
            st.markdown(f"- {icon} `{row['path']}`{extra}")

        section_title("Backups", icon="💾")
        try:
            bm = BackupManager(str(DB_FILE))
            backups = bm.list_recent_backups(10)
            if backups:
                st.dataframe(backups, use_container_width=True, hide_index=True)
            else:
                st.info("No `.db` files in `data/backups/` yet. Use your backup workflow or copy the DB manually.")
        except Exception as e:
            st.warning(str(e))

        st.markdown("---")
        section_title("Audit log (recent)", icon="📜")
        try:
            rows = list_recent_audit(150)
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.caption("No audit entries yet.")
        except Exception as e:
            st.error(str(e))

        st.markdown("---")
        section_title("Admin two-factor authentication (TOTP)", icon="🔐")
        if not ENABLE_ADMIN_2FA:
            st.warning(
                "2FA is **disabled** globally. Set `ENABLE_ADMIN_2FA=true` in `.env` and restart the app to enforce authenticator codes at login."
            )
        else:
            st.success("2FA is **enabled** in settings. Admins can register an authenticator below.")

        self._render_totp_setup()

    def _render_totp_setup(self) -> None:
        sm = SessionManager()
        user = sm.get_current_user()
        if not user or user.get("role") != "admin":
            st.info("Only signed-in admins can manage 2FA here.")
            return

        auth = AuthenticationService()
        email = user["email"]

        st.markdown("Use **Google Authenticator**, **Microsoft Authenticator**, or any TOTP app.")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Generate new secret (invalidates old)", key="totp_gen"):
                ok, secret, uri = auth.generate_admin_totp_secret(email)
                if ok and uri:
                    st.session_state["_totp_uri"] = uri
                    st.session_state["_totp_secret"] = secret or ""
                    st.success("Secret saved (not enabled until you confirm a code).")
                    st.rerun()
                else:
                    st.error("Could not generate secret.")

        if st.session_state.get("_totp_uri"):
            try:
                import qrcode

                img = qrcode.make(st.session_state["_totp_uri"])
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), caption="Scan with your authenticator app", width=220)
            except Exception as e:
                st.caption(f"QR unavailable ({e}). Enter secret manually in app: `{st.session_state.get('_totp_secret', '')}`")

        with col_b:
            with st.form("confirm_totp"):
                code = st.text_input("6-digit code from app", max_chars=8)
                if st.form_submit_button("Confirm and enable 2FA"):
                    if code:
                        ok, msg = auth.confirm_admin_totp(email, code.strip())
                        if ok:
                            st.success(msg)
                            st.session_state.pop("_totp_uri", None)
                            st.session_state.pop("_totp_secret", None)
                            st.rerun()
                        else:
                            st.error(msg)

        with st.form("disable_totp"):
            pwd = st.text_input("Current password (to disable 2FA)", type="password")
            if st.form_submit_button("Disable 2FA"):
                ok, msg = auth.disable_admin_totp(email, pwd)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
