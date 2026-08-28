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
utils.py — Animation and utility methods for LoginDialog.
"""

    def _shake(self) -> None:
        """A simple shake animation for error feedback."""

        def animate(steps_left, x_offset) -> None:
            if steps_left > 0:
                self.geometry(f"+{self.winfo_x() + x_offset}+{self.winfo_y()}")
                self.after(50, lambda: animate(steps_left - 1, -x_offset))

        animate(5, 10)
