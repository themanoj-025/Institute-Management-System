"""Login dialog for the Institute Management System.

UI-focused module that handles the login flow, OTP verification,
email verification, and password reset dialogs.
"""

"""
Desktop login dialog — authenticates against the shared API endpoint.

Replaces the previous local-SQLite authentication with a call to
``POST /v1/auth/login`` over HTTP, so the desktop client and web
dashboard share the same JWT session.

The API base URL is read from the ``API_BASE_URL`` environment variable
(defaults to ``http://localhost:8000`` for local development).
"""

import os
import traceback
import urllib.error

import customtkinter as ctk
from tkinter import TclError

try:
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    SQLAlchemyError = Exception

# Use httpx if available, fall back to urllib.request
try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


from landing.api_auth import (
    ApiAuthError,
    _api_login,
    _api_verify_otp,
    _api_send_verification_email,
    _api_confirm_verification,
    _api_logout,
    _api_forgot_password,
    _api_reset_password,
)
class LoginDialog(ctk.CTkToplevel):


"""
forms.py — Form display methods for LoginDialog.
"""

    def _show_login_form(self) -> None:
        """Return to the login form, hiding OTP, verification, forgot, and reset frames."""
        self._otp_frame.pack_forget()
        self._verify_frame.pack_forget()
        self._forgot_frame.pack_forget()
        self._reset_frame.pack_forget()
        self._login_frame.pack(pady=20)
        self.geometry("400x500")
        self.err_lbl.configure(text="")
        self.btn_login.configure(state="normal", text="Login")

    def _show_otp_verify(self, user_id, username) -> None:
        """Show the OTP verification form after successful login."""
        self._user_id = user_id
        self._username = username
        self._login_frame.pack_forget()
        self._verify_frame.pack_forget()
        self._otp_entry.delete(0, "end")
        self._otp_err.configure(text="")
        self._otp_btn.configure(state="normal", text="Verify OTP")
        self._otp_frame.pack(pady=20)
        self.geometry("400x450")
        self._otp_entry.focus()

    def _show_forgot_form(self) -> None:
        """Show the forgot-password form, hiding login and reset frames."""
        self._login_frame.pack_forget()
        self._otp_frame.pack_forget()
        self._verify_frame.pack_forget()
        self._reset_frame.pack_forget()
        self._forgot_email_entry.delete(0, "end")
        self._forgot_status.configure(text="")
        self._forgot_send_btn.configure(state="normal", text="📧 Send Reset Link")
        # Hide post-send widgets (they may have been shown previously)
        self._forgot_hint_label.pack_forget()
        self._forgot_goto_reset_btn.pack_forget()
        self._forgot_frame.pack(pady=20)
        self.geometry("400x420")
        self._forgot_email_entry.focus()

    def _show_reset_form(self) -> None:
        """Show the reset-password form, hiding login and forgot frames."""
        self._login_frame.pack_forget()
        self._otp_frame.pack_forget()
        self._verify_frame.pack_forget()
        self._forgot_frame.pack_forget()
        self._reset_token_entry.delete(0, "end")
        self._reset_pass_entry.delete(0, "end")
        self._reset_confirm_entry.delete(0, "end")
        self._reset_status.configure(text="")
        self._reset_btn.configure(state="normal", text="🔑 Reset Password")
        self._reset_frame.pack(pady=20)
        self.geometry("400x480")
        self._reset_token_entry.focus()

    def _show_verification_prompt(self, user_id, username) -> None:
        """Show the email verification prompt when login fails due to unverified email.

        If ``user_id`` is not available from the failed login response (the API returns
        401 without user_id), resolve it from the local database by username.
        """
        if not user_id and username:
            try:
                from database.models import User

                user = self.db_session.query(User).filter(User.username == username).first()
                if user:
                    user_id = user.id
            except (SQLAlchemyError, OSError):
                pass  # Non-blocking — user can still go back
        self._user_id = user_id or None
        self._username = username
        self._login_frame.pack_forget()
        self._otp_frame.pack_forget()
        self._verify_status.configure(text="")
        self._verify_token_entry.delete(0, "end")
        self._verify_send_btn.configure(state="normal", text="📧 Send Verification Email")
        self._verify_confirm_btn.configure(state="normal")
        self._verify_frame.pack(pady=20)
        self.geometry("400x520")

    # ── Login Step ────────────────────────────────────────────────

    def _do_login(self) -> None:
