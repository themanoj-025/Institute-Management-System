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

import customtkinter as ctk

# Use httpx if available, fall back to urllib.request
try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


class ApiAuthError(Exception):
    """Raised when the API returns an authentication error."""


# API Helper Functions


def _api_login(username: str, password: str) -> dict:
    """Call ``POST /v1/auth/login`` and return the response.

    The endpoint now returns ``{"status": "otp_required", "user_id": ...}``
    instead of an access_token. The user must verify OTP at
    ``/v1/auth/verify-otp`` to receive a JWT.
    """
    url = f"{API_BASE_URL}/v1/auth/login"
    payload = {"username": username, "password": password}

    if _HTTPX_AVAILABLE:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 401:
                msg = resp.json().get("error", {}).get("message", "Invalid credentials")
                raise ApiAuthError(msg)
            if resp.status_code != 200:
                raise ApiAuthError(f"Server returned status {resp.status_code}")
            return resp.json()
        except httpx.RequestError as e:
            raise ApiAuthError(f"Could not connect to server: {e}")
    else:
        import json as _json
        import urllib.error
        import urllib.request

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                if resp.status == 401:
                    raise ApiAuthError("Invalid credentials")
                return _json.loads(body)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                msg = _json.loads(body).get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            raise ApiAuthError(msg)
        except urllib.error.URLError as e:
            raise ApiAuthError(f"Could not connect to server: {e.reason}")


def _api_verify_otp(user_id: int, otp: str) -> dict:
    """Call ``POST /v1/auth/verify-otp`` with the OTP code.

    Returns the response containing ``access_token``, ``role``, and ``user``.
    """
    url = f"{API_BASE_URL}/v1/auth/verify-otp"
    payload = {"user_id": user_id, "otp": otp}

    if _HTTPX_AVAILABLE:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 401:
                msg = resp.json().get("error", {}).get("message", "Invalid OTP")
                raise ApiAuthError(msg)
            if resp.status_code != 200:
                raise ApiAuthError(f"OTP verification failed (status {resp.status_code})")
            return resp.json()
        except httpx.RequestError as e:
            raise ApiAuthError(f"Could not connect to server: {e}")
    else:
        import json as _json
        import urllib.error
        import urllib.request

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return _json.loads(body)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                msg = _json.loads(body).get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            raise ApiAuthError(msg)
        except urllib.error.URLError as e:
            raise ApiAuthError(f"Could not connect to server: {e.reason}")


def _api_send_verification_email(user_id: int) -> dict:
    """Call ``POST /v1/auth/verify-email/send`` to request a new verification email."""
    url = f"{API_BASE_URL}/v1/auth/verify-email/send"
    payload = {
        "user_id": user_id,
        "otp": "000000",
    }  # otp required by schema, ignored here

    if _HTTPX_AVAILABLE:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 404:
                raise ApiAuthError("User not found")
            if resp.status_code == 400:
                msg = resp.json().get("error", {}).get("message", "Request failed")
                raise ApiAuthError(msg)
            if resp.status_code != 200:
                raise ApiAuthError(f"Verification request failed (status {resp.status_code})")
            return resp.json()
        except httpx.RequestError as e:
            raise ApiAuthError(f"Could not connect to server: {e}")
    else:
        import json as _json
        import urllib.error
        import urllib.request

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return _json.loads(body)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                msg = _json.loads(body).get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            raise ApiAuthError(msg)
        except urllib.error.URLError as e:
            raise ApiAuthError(f"Could not connect to server: {e.reason}")


def _api_confirm_verification(user_id: int, token: str) -> dict:
    """Call ``POST /v1/auth/verify-email/confirm`` with the verification token."""
    url = f"{API_BASE_URL}/v1/auth/verify-email/confirm"
    payload = {"user_id": user_id, "otp": token}

    if _HTTPX_AVAILABLE:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 401:
                msg = resp.json().get("error", {}).get("message", "Invalid or expired token")
                raise ApiAuthError(msg)
            if resp.status_code != 200:
                raise ApiAuthError(f"Verification failed (status {resp.status_code})")
            return resp.json()
        except httpx.RequestError as e:
            raise ApiAuthError(f"Could not connect to server: {e}")
    else:
        import json as _json
        import urllib.error
        import urllib.request

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return _json.loads(body)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                msg = _json.loads(body).get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            raise ApiAuthError(msg)
        except urllib.error.URLError as e:
            raise ApiAuthError(f"Could not connect to server: {e.reason}")


def _api_logout(token: str) -> bool:
    """Call ``POST /v1/auth/logout`` to blacklist the token.

    Returns ``True`` if the token was successfully blacklisted.
    """
    url = f"{API_BASE_URL}/v1/auth/logout"
    headers = {"Authorization": f"Bearer {token}"}

    if _HTTPX_AVAILABLE:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers)
            return resp.status_code == 200
        except Exception:
            return False
    else:
        import urllib.request

        req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10):
                return True
        except Exception:
            return False


def _api_forgot_password(email: str) -> dict:
    """Call ``POST /v1/auth/forgot-password`` to request a password reset.

    Always returns a generic success response regardless of whether the
    email exists (prevents user enumeration).
    """
    url = f"{API_BASE_URL}/v1/auth/forgot-password"
    payload = {"email": email}

    if _HTTPX_AVAILABLE:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 429:
                raise ApiAuthError("Too many requests. Please try again later.")
            if resp.status_code != 200:
                raise ApiAuthError(f"Server returned status {resp.status_code}")
            return resp.json()
        except httpx.RequestError as e:
            raise ApiAuthError(f"Could not connect to server: {e}")
    else:
        import json as _json
        import urllib.error
        import urllib.request

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return _json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise ApiAuthError("Too many requests. Please try again later.")
            body = e.read().decode("utf-8", errors="replace")
            try:
                msg = _json.loads(body).get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            raise ApiAuthError(msg)
        except urllib.error.URLError as e:
            raise ApiAuthError(f"Could not connect to server: {e.reason}")


def _api_reset_password(user_id: int, token: str, new_password: str) -> dict:
    """Call ``POST /v1/auth/reset-password`` to complete the password reset.

    The token is single-use and expires after 30 minutes.
    """
    url = f"{API_BASE_URL}/v1/auth/reset-password"
    payload = {"user_id": user_id, "token": token, "new_password": new_password}

    if _HTTPX_AVAILABLE:
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, json=payload)
            if resp.status_code == 400:
                msg = resp.json().get("error", {}).get("message", "Reset failed")
                raise ApiAuthError(msg)
            if resp.status_code == 429:
                raise ApiAuthError("Too many requests. Please try again later.")
            if resp.status_code != 200:
                raise ApiAuthError(f"Server returned status {resp.status_code}")
            return resp.json()
        except httpx.RequestError as e:
            raise ApiAuthError(f"Could not connect to server: {e}")
    else:
        import json as _json
        import urllib.error
        import urllib.request

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return _json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise ApiAuthError("Too many requests. Please try again later.")
            body = e.read().decode("utf-8", errors="replace")
            try:
                msg = _json.loads(body).get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            raise ApiAuthError(msg)
        except urllib.error.URLError as e:
            raise ApiAuthError(f"Could not connect to server: {e.reason}")


# Login Dialog


class LoginDialog(ctk.CTkToplevel):
    """Desktop login dialog that authenticates via the shared API.

    Flow:
    1. User enters username + password → POST /v1/auth/login
    2. If email not verified → show verification prompt with Send/Confirm buttons
    3. If verified + correct password → show OTP input dialog
    4. After OTP verification → JWT received → session starts
    """

    def __init__(self, master, tm, role, db_session, app_state, success_cb, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.tm = tm
        self.role = role
        self.db_session = db_session
        self.app_state = app_state
        self.success_cb = success_cb

        self._user_id = None
        self._username = None
        self._password = None

        self.title(f"{role.capitalize()} Login")
        self.geometry("400x500")
        self.attributes("-topmost", True)
        self.grab_set()

        # Color based on role
        colors = {
            "admin": tm.danger_color,
            "staff": tm.success_color,
            "student": tm.accent_color,
        }
        color = colors.get(role, tm.accent_color)
        self._accent_color = color

        self.frame = ctk.CTkFrame(self, border_width=2, border_color=color)
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            self.frame,
            text=f"{role.capitalize()} Portal",
            font=self.tm.header_font,
            text_color=color,
        ).pack(pady=(30, 20))

        # ── Login Form ──────────────────────────────────────────────
        self._login_frame = ctk.CTkFrame(self.frame, fg_color="transparent")

        self.user_entry = ctk.CTkEntry(self._login_frame, placeholder_text="Username", width=250)
        self.user_entry.pack(pady=10)

        self.pass_entry = ctk.CTkEntry(
            self._login_frame, placeholder_text="Password", width=250, show="*"
        )
        self.pass_entry.pack(pady=10)

        self.err_lbl = ctk.CTkLabel(self._login_frame, text="")
        self.err_lbl.pack(pady=5)

        self.btn_login = ctk.CTkButton(
            self._login_frame,
            text="Login",
            fg_color=color,
            width=250,
            command=self._do_login,
        )
        self.btn_login.pack(pady=10)

        # ── Forgot Password Link ────────────────────────────────────
        self._forgot_link = ctk.CTkLabel(
            self._login_frame,
            text="Forgot password?",
            font=ctk.CTkFont(size=12, underline=True),
            text_color="gray",
            cursor="hand2",
        )
        self._forgot_link.pack(pady=(0, 5))
        self._forgot_link.bind("<Button-1>", lambda e: self._show_forgot_form())

        self._login_frame.pack(pady=20)

        # ── OTP Verification Frame (hidden initially) ───────────────
        self._otp_frame = ctk.CTkFrame(self.frame, fg_color="transparent")

        ctk.CTkLabel(
            self._otp_frame,
            text="OTP Verification",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=color,
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            self._otp_frame,
            text="A one-time password was sent to your email.\nEnter the 6-digit code below:",
            font=self.tm.small_font,
            text_color="gray",
            justify="center",
        ).pack(pady=(0, 10))

        self._otp_entry = ctk.CTkEntry(
            self._otp_frame,
            placeholder_text="000000",
            width=200,
            font=ctk.CTkFont(size=20),
        )
        self._otp_entry.pack(pady=5)

        self._otp_err = ctk.CTkLabel(self._otp_frame, text="")
        self._otp_err.pack(pady=5)

        self._otp_btn = ctk.CTkButton(
            self._otp_frame,
            text="Verify OTP",
            fg_color=color,
            width=200,
            command=self._do_verify_otp,
        )
        self._otp_btn.pack(pady=5)

        self._otp_back_btn = ctk.CTkButton(
            self._otp_frame,
            text="← Back to Login",
            fg_color="gray",
            width=200,
            command=self._show_login_form,
        )
        self._otp_back_btn.pack(pady=5)

        # ── Email Verification Frame (hidden initially) ─────────────
        self._verify_frame = ctk.CTkFrame(self.frame, fg_color="transparent")

        ctk.CTkLabel(
            self._verify_frame,
            text="Email Verification Required",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=color,
        ).pack(pady=(15, 5))

        self._verify_msg = ctk.CTkLabel(
            self._verify_frame,
            text="Your email address has not been verified yet.\nPlease click 'Send Verification Email' to get\na verification link sent to your inbox.",
            font=self.tm.small_font,
            text_color="gray",
            justify="center",
        )
        self._verify_msg.pack(pady=(0, 10))

        self._verify_send_btn = ctk.CTkButton(
            self._verify_frame,
            text="📧 Send Verification Email",
            fg_color=color,
            width=250,
            command=self._do_send_verification,
        )
        self._verify_send_btn.pack(pady=5)

        self._verify_status = ctk.CTkLabel(self._verify_frame, text="")
        self._verify_status.pack(pady=5)

        ctk.CTkLabel(
            self._verify_frame,
            text="Already have a verification code? Enter it below:",
            font=self.tm.small_font,
            text_color="gray",
            justify="center",
        ).pack(pady=(10, 5))

        self._verify_token_entry = ctk.CTkEntry(
            self._verify_frame, placeholder_text="Verification token", width=250
        )
        self._verify_token_entry.pack(pady=5)

        self._verify_confirm_btn = ctk.CTkButton(
            self._verify_frame,
            text="Confirm Verification",
            fg_color="green",
            width=200,
            command=self._do_confirm_verification,
        )
        self._verify_confirm_btn.pack(pady=5)

        self._verify_back_btn = ctk.CTkButton(
            self._verify_frame,
            text="← Back to Login",
            fg_color="gray",
            width=200,
            command=self._show_login_form,
        )
        self._verify_back_btn.pack(pady=5)

        # ── Forgot Password Frame (hidden initially) ───────────────
        self._forgot_frame = ctk.CTkFrame(self.frame, fg_color="transparent")

        ctk.CTkLabel(
            self._forgot_frame,
            text="Forgot Password",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=color,
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            self._forgot_frame,
            text="Enter your email address to receive\na password reset link.",
            font=self.tm.small_font,
            text_color="gray",
            justify="center",
        ).pack(pady=(0, 10))

        self._forgot_email_entry = ctk.CTkEntry(
            self._forgot_frame, placeholder_text="Your registered email", width=250
        )
        self._forgot_email_entry.pack(pady=10)

        self._forgot_status = ctk.CTkLabel(self._forgot_frame, text="", wraplength=300)
        self._forgot_status.pack(pady=5)

        self._forgot_send_btn = ctk.CTkButton(
            self._forgot_frame,
            text="📧 Send Reset Link",
            fg_color=color,
            width=250,
            command=self._do_forgot_password,
        )
        self._forgot_send_btn.pack(pady=5)

        self._forgot_back_btn = ctk.CTkButton(
            self._forgot_frame,
            text="← Back to Login",
            fg_color="gray",
            width=200,
            command=self._show_login_form,
        )
        self._forgot_back_btn.pack(pady=5)

        # ── Post-send hint label & goto-reset button (hidden initially) ─
        self._forgot_hint_label = ctk.CTkLabel(
            self._forgot_frame,
            text="",
            font=self.tm.small_font,
            text_color="gray",
            justify="center",
        )
        self._forgot_goto_reset_btn = ctk.CTkButton(
            self._forgot_frame,
            text="🔑 Enter Reset Token",
            fg_color=self._accent_color,
            width=200,
            command=self._show_reset_form,
        )

        # ── Reset Password Frame (hidden initially) ────────────────
        self._reset_frame = ctk.CTkFrame(self.frame, fg_color="transparent")

        ctk.CTkLabel(
            self._reset_frame,
            text="Reset Password",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=color,
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            self._reset_frame,
            text="Enter the reset token from your email\nand choose a new password.",
            font=self.tm.small_font,
            text_color="gray",
            justify="center",
        ).pack(pady=(0, 10))

        self._reset_token_entry = ctk.CTkEntry(
            self._reset_frame, placeholder_text="Reset token from email", width=250
        )
        self._reset_token_entry.pack(pady=8)

        self._reset_pass_entry = ctk.CTkEntry(
            self._reset_frame, placeholder_text="New password", width=250, show="*"
        )
        self._reset_pass_entry.pack(pady=8)

        self._reset_confirm_entry = ctk.CTkEntry(
            self._reset_frame,
            placeholder_text="Confirm new password",
            width=250,
            show="*",
        )
        self._reset_confirm_entry.pack(pady=8)

        self._reset_status = ctk.CTkLabel(self._reset_frame, text="", wraplength=300)
        self._reset_status.pack(pady=5)

        self._reset_btn = ctk.CTkButton(
            self._reset_frame,
            text="🔑 Reset Password",
            fg_color=color,
            width=250,
            command=self._do_reset_password,
        )
        self._reset_btn.pack(pady=5)

        self._reset_back_btn = ctk.CTkButton(
            self._reset_frame,
            text="← Back to Login",
            fg_color="gray",
            width=200,
            command=self._show_login_form,
        )
        self._reset_back_btn.pack(pady=5)

        # Demo mode — show credentials only if DEMO_MODE=true
        if os.environ.get("DEMO_MODE", "false").lower() == "true":
            self.demo_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
            self.demo_frame.pack(pady=20)
            demo_creds = os.environ.get(
                f"DEMO_CREDS_{role.upper()}",
                f"{role} / demo-{role.lower()}",
            )
            ctk.CTkLabel(self.demo_frame, text=f"Demo: {demo_creds}", text_color="gray").pack()

    # ── UI Navigation ──────────────────────────────────────────────

    def _show_login_form(self):
        """Return to the login form, hiding OTP, verification, forgot, and reset frames."""
        self._otp_frame.pack_forget()
        self._verify_frame.pack_forget()
        self._forgot_frame.pack_forget()
        self._reset_frame.pack_forget()
        self._login_frame.pack(pady=20)
        self.geometry("400x500")
        self.err_lbl.configure(text="")
        self.btn_login.configure(state="normal", text="Login")

    def _show_otp_verify(self, user_id, username):
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

    def _show_forgot_form(self):
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

    def _show_reset_form(self):
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

    def _show_verification_prompt(self, user_id, username):
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
            except Exception:
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

    def _do_login(self):
        """Authenticate via the shared API endpoint."""
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not username or not password:
            self.err_lbl.configure(text="Please enter username and password", text_color="red")
            self._shake()
            return

        try:
            self.btn_login.configure(state="disabled", text="Authenticating...")
            self.err_lbl.configure(text="", text_color="")

            result = _api_login(username, password)
            api_role = result.get("role", "")
            user_id = result.get("user_id")

            if api_role and api_role != self.role:
                self.btn_login.configure(state="normal", text="Login")
                self.err_lbl.configure(
                    text=f"User is not a {self.role}",
                    text_color="red",
                )
                self._shake()
                return

            # Login succeeded — show OTP verification
            if user_id:
                self._show_otp_verify(user_id, username)
            else:
                self.err_lbl.configure(text="Unexpected server response", text_color="red")
                self._shake()

        except ApiAuthError as e:
            error_text = str(e)
            self.btn_login.configure(state="normal", text="Login")

            # Check if the error message indicates unverified email
            if "verify your email" in error_text.lower():
                self._show_verification_prompt(None, username)
            else:
                self.err_lbl.configure(text=error_text, text_color="red")
                self._shake()
        except Exception as e:
            traceback.print_exc()
            self.err_lbl.configure(text=f"Connection error: {e}", text_color="red")
            self._shake()
        finally:
            try:
                self.btn_login.configure(state="normal", text="Login")
            except Exception:
                pass

    # ── OTP Verification Step ─────────────────────────────────────

    def _do_verify_otp(self):
        """Verify the OTP and receive the JWT."""
        otp = self._otp_entry.get().strip()

        if not otp or not otp.isdigit() or len(otp) != 6:
            self._otp_err.configure(text="Please enter a 6-digit OTP code", text_color="red")
            self._shake()
            return

        try:
            self._otp_btn.configure(state="disabled", text="Verifying...")
            self._otp_err.configure(text="", text_color="")

            result = _api_verify_otp(self._user_id, otp)

            access_token = result.get("access_token", "")
            api_role = result.get("role", "")

            if not access_token:
                self._otp_err.configure(text="Server did not return a token", text_color="red")
                self._shake()
                return

            # Store JWT in app state
            self.app_state.current_user = {
                "username": self._username,
                "role": api_role,
                "access_token": access_token,
            }

            # Attach token to the master's session tracker
            master = self.winfo_toplevel()
            if hasattr(master, "session_tracker"):
                master.session_tracker.set_token(access_token)

            self.destroy()
            self.success_cb()

        except ApiAuthError as e:
            self._otp_err.configure(text=str(e), text_color="red")
            self._shake()
        except Exception as e:
            traceback.print_exc()
            self._otp_err.configure(text=f"Error: {e}", text_color="red")
            self._shake()
        finally:
            try:
                self._otp_btn.configure(state="normal", text="Verify OTP")
            except Exception:
                pass

    # ── Email Verification Step ───────────────────────────────────

    def _do_send_verification(self):
        """Send a verification email to the user."""
        if not self._user_id:
            # We don't have user_id from the failed login — can't send
            self._verify_status.configure(
                text="Could not determine user ID. Please contact support.",
                text_color="red",
            )
            return

        try:
            self._verify_send_btn.configure(state="disabled", text="Sending...")
            self._verify_status.configure(text="", text_color="")

            result = _api_send_verification_email(self._user_id)

            status = result.get("status", "")
            if status == "already_verified":
                self._verify_status.configure(
                    text="✅ Your email is already verified! You can now log in.",
                    text_color="green",
                )
                self._verify_send_btn.configure(state="disabled", text="Already Verified")
                # Enable back to login
                self._verify_back_btn.configure(
                    text="← Back to Login (try again)",
                    fg_color=self._accent_color,
                )
            elif status == "sent":
                self._verify_status.configure(
                    text="✅ Verification email sent!\nCheck your inbox and enter the code below.",
                    text_color="green",
                )
                self._verify_send_btn.configure(state="normal", text="📧 Resend Email")
                self._verify_token_entry.focus()
            else:
                self._verify_status.configure(
                    text=f"Unexpected response: {result.get('message', '')}",
                    text_color="orange",
                )
                self._verify_send_btn.configure(state="normal", text="📧 Send Verification Email")

        except ApiAuthError as e:
            self._verify_status.configure(text=str(e), text_color="red")
            self._verify_send_btn.configure(state="normal", text="📧 Send Verification Email")
            self._shake()
        except Exception as e:
            traceback.print_exc()
            self._verify_status.configure(text=f"Error: {e}", text_color="red")
            self._verify_send_btn.configure(state="normal", text="📧 Send Verification Email")
            self._shake()

    def _do_confirm_verification(self):
        """Confirm the email verification token."""
        token = self._verify_token_entry.get().strip()

        if not token or len(token) < 6:
            self._verify_status.configure(
                text="Please enter the verification token from your email.",
                text_color="red",
            )
            self._shake()
            return

        if not self._user_id:
            self._verify_status.configure(
                text="Could not determine user ID. Please go back and log in again.",
                text_color="red",
            )
            return

        try:
            self._verify_confirm_btn.configure(state="disabled", text="Verifying...")
            self._verify_status.configure(text="", text_color="")

            result = _api_confirm_verification(self._user_id, token)

            if result.get("status") == "verified":
                self._verify_status.configure(
                    text="✅ Email verified successfully!\nClick 'Back to Login' to sign in.",
                    text_color="green",
                )
                self._verify_confirm_btn.configure(state="disabled", text="✅ Verified")
                self._verify_send_btn.configure(state="disabled")
                self._verify_back_btn.configure(
                    text="← Back to Login (verified)",
                    fg_color=self._accent_color,
                )
            else:
                self._verify_status.configure(
                    text=f"Verification failed: {result.get('message', '')}",
                    text_color="red",
                )
                self._verify_confirm_btn.configure(state="normal", text="Confirm Verification")

        except ApiAuthError as e:
            self._verify_status.configure(text=str(e), text_color="red")
            self._verify_confirm_btn.configure(state="normal", text="Confirm Verification")
            self._shake()
        except Exception as e:
            traceback.print_exc()
            self._verify_status.configure(text=f"Error: {e}", text_color="red")
            self._verify_confirm_btn.configure(state="normal", text="Confirm Verification")
            self._shake()

    # ── Forgot Password Step ──────────────────────────────────────

    def _do_forgot_password(self):
        """Request a password reset email."""
        email = self._forgot_email_entry.get().strip()

        if not email or "@" not in email:
            self._forgot_status.configure(
                text="Please enter a valid email address.", text_color="red"
            )
            self._shake()
            return

        try:
            self._forgot_send_btn.configure(state="disabled", text="Sending...")
            self._forgot_status.configure(text="", text_color="")

            result = _api_forgot_password(email)

            message = result.get(
                "message",
                "If an account with that email exists, a reset link has been sent.",
            )
            self._forgot_status.configure(text=f"✅ {message}", text_color="green")
            self._forgot_send_btn.configure(state="normal", text="📧 Resend Reset Link")

            # Show hint label and goto-reset button (pre-created in __init__)
            self._forgot_hint_label.configure(
                text="\nCheck your email for the reset token,\nthen click below to reset your password."
            )
            self._forgot_hint_label.pack(pady=(5, 2))
            self._forgot_goto_reset_btn.pack(pady=5)

        except ApiAuthError as e:
            self._forgot_status.configure(text=str(e), text_color="red")
            self._forgot_send_btn.configure(state="normal", text="📧 Send Reset Link")
            self._shake()
        except Exception as e:
            traceback.print_exc()
            self._forgot_status.configure(text=f"Error: {e}", text_color="red")
            self._forgot_send_btn.configure(state="normal", text="📧 Send Reset Link")
            self._shake()

    # ── Reset Password Step ────────────────────────────────────────

    def _do_reset_password(self):
        """Complete the password reset with token + new password."""
        token = self._reset_token_entry.get().strip()
        new_password = self._reset_pass_entry.get()
        confirm_password = self._reset_confirm_entry.get()

        if not token:
            self._reset_status.configure(
                text="Please enter the reset token from your email.", text_color="red"
            )
            self._shake()
            return

        if len(new_password) < 8:
            self._reset_status.configure(
                text="Password must be at least 8 characters.", text_color="red"
            )
            self._shake()
            return

        if new_password != confirm_password:
            self._reset_status.configure(text="Passwords do not match.", text_color="red")
            self._shake()
            return

        # Validate password strength (matches backend policy)
        import re

        if not re.search(r"[A-Z]", new_password):
            self._reset_status.configure(
                text="Password must contain an uppercase letter.", text_color="red"
            )
            self._shake()
            return
        if not re.search(r"[a-z]", new_password):
            self._reset_status.configure(
                text="Password must contain a lowercase letter.", text_color="red"
            )
            self._shake()
            return
        if not re.search(r"[0-9]", new_password):
            self._reset_status.configure(text="Password must contain a digit.", text_color="red")
            self._shake()
            return
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", new_password):
            self._reset_status.configure(
                text="Password must contain a special character.", text_color="red"
            )
            self._shake()
            return

        # Try to resolve user_id from the local database using the logged-in
        # user's email if available, or prompt the user to enter it
        user_id = None
        if hasattr(self.app_state, "current_user") and self.app_state.current_user:
            username = self.app_state.current_user.get("username")
            if username:
                try:
                    from database.models import User

                    user = self.db_session.query(User).filter(User.username == username).first()
                    if user:
                        user_id = user.id
                except Exception:
                    pass

        if not user_id:
            # Ask the user for their user ID via a simple prompt
            from customtkinter import CTkInputDialog

            id_dialog = CTkInputDialog(
                text="Enter your User ID (the number from your reset email):",
                title="User ID Required",
            )
            id_input = id_dialog.get_input()
            if not id_input or not id_input.strip().isdigit():
                self._reset_status.configure(
                    text="A valid User ID is required. Check your reset email.",
                    text_color="red",
                )
                self._shake()
                return
            user_id = int(id_input.strip())

        try:
            self._reset_btn.configure(state="disabled", text="Resetting...")
            self._reset_status.configure(text="", text_color="")

            result = _api_reset_password(user_id, token, new_password)

            message = result.get("message", "Password reset successfully!")
            self._reset_status.configure(
                text=f"✅ {message}\nYou can now log in with your new password.",
                text_color="green",
            )
            self._reset_btn.configure(state="disabled", text="✅ Done")

            # Show a button to go back to login
            self._reset_back_btn.configure(
                text="← Back to Login (sign in)",
                fg_color=self._accent_color,
            )

        except ApiAuthError as e:
            self._reset_status.configure(text=str(e), text_color="red")
            self._reset_btn.configure(state="normal", text="🔑 Reset Password")
            self._shake()
        except Exception as e:
            traceback.print_exc()
            self._reset_status.configure(text=f"Error: {e}", text_color="red")
            self._reset_btn.configure(state="normal", text="🔑 Reset Password")
            self._shake()

    # ── Shake Animation ───────────────────────────────────────────

    def _shake(self):
        """A simple shake animation for error feedback."""

        def animate(steps_left, x_offset):
            if steps_left > 0:
                self.geometry(f"+{self.winfo_x() + x_offset}+{self.winfo_y()}")
                self.after(50, lambda: animate(steps_left - 1, -x_offset))

        animate(5, 10)
