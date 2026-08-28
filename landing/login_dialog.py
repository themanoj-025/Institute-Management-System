"""
login_dialog.py — Login dialog for Institute Management System

.. note::

   The implementation has been refactored into ``login_pkg/``
   for maintainability.  This module re-exports ``LoginDialog``
   so existing ``from landing.login_dialog import LoginDialog``
   imports continue to work unchanged.
"""

from landing.login_pkg import LoginDialog

__all__ = ["LoginDialog"]
