"""
Desktop notifications with delivery-status reporting (audit item 8.6).

``notify()`` previously fired a daemon thread, printed failures to stdout and
gave the caller no way to know whether the OS notification was delivered. It
now returns a result handle and supports an ``on_complete`` callback carrying
a :class:`NotificationResult` (``sent`` / ``failed`` + error detail) so UIs
can raise a toast on failure.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from config.constants import APP_NAME

logger = logging.getLogger("bb-ims.notifier")

# Lock protecting plyer calls: plyer's win10 backend is not thread-safe and
# concurrent notifications could interleave badly.
_notify_lock = threading.Lock()


@dataclass
class NotificationResult:
    """Outcome of one desktop-notification delivery attempt."""

    status: str  # "sent" | "failed"
    title: str = ""
    error: str | None = None
    error_type: str | None = None


@dataclass
class NotificationHandle:
    """Awaitable handle for a notification dispatched on a worker thread."""

    title: str
    _done: threading.Event = field(default_factory=threading.Event, repr=False)
    _result: NotificationResult | None = None

    def wait(self, timeout: float | None = None) -> NotificationResult | None:
        """Block until delivery finishes; returns the result (None on timeout)."""
        self._done.wait(timeout)
        return self._result

    def _finish(self, result: NotificationResult) -> None:
        self._result = result
        self._done.set()


def _deliver(title: str, message: str, timeout: int, icon_path: str | None) -> NotificationResult:
    """Blocking delivery attempt, returning a structured result."""
    try:
        from plyer import notification

        with _notify_lock:
            notification.notify(
                title=f"{APP_NAME} - {title}",
                message=message,
                app_name=APP_NAME,
                app_icon=icon_path,  # Must be .ico on Windows
                timeout=timeout,
            )
        return NotificationResult(status="sent", title=title)
    except Exception as exc:
        # exceptions (OSError, NotImplementedError, NotifyFailure, ...); we
        # must capture any of them into a failed result rather than crash the
        # thread.
        return NotificationResult(
            status="failed", title=title, error=str(exc), error_type=type(exc).__name__
        )


def _toast_failure(root: Any, result: NotificationResult) -> None:
    """Raise a UI toast for a failed notification, on the Tk thread."""

    def _show() -> None:
        try:
            from ui.toast import ToastManager

            ToastManager.show(
                root,
                f"Desktop notification failed: {result.error or result.error_type}",
                "error",
            )
        except Exception:
            logger.warning("Could not show failure toast: no UI available")

    try:
        root.after(0, _show)
    except Exception:
        logger.warning("Could not schedule failure toast: root unavailable")


class DesktopNotifier:
    def __init__(self) -> None:
        # Path to app icon if any
        self.icon_path: str | None = None
        # Could point to an .ico file in assets/icons/ if needed

    def notify(
        self,
        title: str,
        message: str,
        timeout: int = 5,
        on_complete: Callable[[NotificationResult], None] | None = None,
        root: Any = None,
    ) -> NotificationHandle:
        """Show a desktop notification and report delivery status.

        Returns a :class:`NotificationHandle` immediately; ``on_complete`` is
        invoked on the worker thread with the :class:`NotificationResult`
        once delivery finished (success or failure).

        When ``root`` (a Tk widget) is provided, a failed delivery also raises
        an error toast in the UI (marshalled onto the Tk thread via
        ``root.after``) so silent notification loss is visible (audit 8.6).
        """

        def task() -> None:
            result = _deliver(title, message, timeout, self.icon_path)
            if result.status == "failed":
                logger.error(
                    "Desktop notification failed: %s (%s)",
                    result.error,
                    result.error_type,
                )
                if root is not None:
                    _toast_failure(root, result)
            if on_complete is not None:
                try:
                    on_complete(result)
                except Exception:
                    logger.exception("on_complete callback raised")

        handle = NotificationHandle(title=title)
        threading.Thread(target=task, daemon=True).start()
        return handle


desktop_notifier = DesktopNotifier()
