"""
login_pkg — Backward-compatible re-exporter.

Form display, action handlers, and animation helpers live in focused sub-modules.
This file re-exports ``LoginDialog`` so existing
``from landing.login_dialog import LoginDialog``
continues to work unchanged.
"""

from landing.login_pkg.dialog import LoginDialog  # noqa: F401

__all__ = ["LoginDialog"]
