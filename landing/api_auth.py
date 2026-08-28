"""API authentication helpers for the login dialog.

Extracted from login_dialog.py to keep the dialog class focused on UI logic.
These functions handle HTTP communication with the backend API for
login, OTP verification, email verification, and password reset.
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
            except (ValueError, KeyError, TypeError):
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
            except (ValueError, KeyError, TypeError):
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
            except (ValueError, KeyError, TypeError):
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
            except (ValueError, KeyError, TypeError):
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
        except (httpx.RequestError, OSError):
            return False
    else:
        import urllib.request

        req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10):
                return True
        except (urllib.error.URLError, OSError):
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
            except (ValueError, KeyError, TypeError):
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
            except (ValueError, KeyError, TypeError):
                msg = str(e)
            raise ApiAuthError(msg)
        except urllib.error.URLError as e:
            raise ApiAuthError(f"Could not connect to server: {e.reason}")


# Login Dialog
