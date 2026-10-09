"""Course catalog data for the Institute Management System."""

from config.courses_pkg import AVAILABLE_COURSES

# Backward-compatible alias: tests and callers expect ``COURSES``.
COURSES = AVAILABLE_COURSES

__all__ = ["AVAILABLE_COURSES", "COURSES"]
