"""
JWT-based session tracker for the desktop client.

Now validates JWT expiry instead of using a local timer, and provides
logout functionality that calls the API's /v1/auth/logout endpoint
to blacklist the token server-side.

The desktop client authenticates against POST /v1/auth/login (same as
the web dashboard), so both surfaces share the same JWT session.
"""

import logging
from datetime import datetime
from tkinter import TclError
from typing import Optional

from utils.time import utc_now

logger = logging.getLogger("bb-ims.session")


class SessionTracker:
    """Tracks the desktop session using JWT token validation.

    Parameters
    ----------
    logout_callback : callable
        Invoked when the session expires or user logs out.
    root : tk.Widget
        Root window for ``after()`` scheduling.
    timeout_minutes : int
        Idle timeout in minutes (default 30). The session tracker
        monitors user activity and auto-logs out after inactivity.
    """

    def __init__(self, logout_callback, root, timeout_minutes=30) -> None:
        self.logout_callback = logout_callback
        self.root = root
        self.timeout_minutes = timeout_minutes
        self.last_activity = utc_now()
        self.is_active = False
        self._timer_id = None
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

    def set_token(self, access_token: str, expires_at: datetime | None = None) -> None:
        """Store the JWT for this session.

        Parameters
        ----------
        access_token : str
            The JWT Bearer token obtained from POST /v1/auth/login.
        expires_at : datetime, optional
            Token expiry time. If not provided, the token is treated
            as valid until manually logged out.
        """
        self._access_token = access_token
        self._token_expiry = expires_at

    def get_token(self) -> str | None:
        """Return the stored JWT, or None if expired."""
        if self._access_token is None:
            return None
        if self._token_expiry and utc_now() >= self._token_expiry:
            logger.info("JWT has expired — clearing stored token")
            self._access_token = None
            self._token_expiry = None
            return None
        return self._access_token

    def clear_token(self) -> None:
        """Clear the stored JWT (called on logout)."""
        self._access_token = None
        self._token_expiry = None

    def is_token_valid(self) -> bool:
        """Check if the stored token is still valid (not expired)."""
        return self.get_token() is not None

    def start(self) -> None:
        """Begin session tracking."""
        self.is_active = True
        self.last_activity = utc_now()
        self._check_timeout()

    def stop(self) -> None:
        """Stop session tracking and clear the token."""
        self.is_active = False
        self.clear_token()
        if self._timer_id:
            try:
                self.root.after_cancel(self._timer_id)
            except (TclError, OSError):
                pass
            self._timer_id = None

    def update_activity(self, event=None) -> None:
        """Reset the idle timer on user activity."""
        if self.is_active:
            self.last_activity = utc_now()

    def _check_timeout(self) -> None:
        """Check if the session has timed out due to inactivity.

        Called every 60 seconds via ``after()``.
        """
        if not self.is_active:
            return

        now = utc_now()
        diff = (now - self.last_activity).total_seconds() / 60

        if diff >= self.timeout_minutes:
            logger.info("Session timed out after %d minutes of inactivity", self.timeout_minutes)
            self.stop()
            self.logout_callback()
        else:
            self._timer_id = self.root.after(60000, self._check_timeout)
