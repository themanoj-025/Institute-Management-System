"""Tests for auth.RoleGuard."""

import pytest

from auth.role_guard import RoleGuard


class TestRoleGuard:
    """Tests for RoleGuard.check_access."""

    def test_admin_has_access(self) -> None:
        assert RoleGuard.check_access("admin", ["admin", "staff"]) is True

    def test_staff_has_access(self) -> None:
        assert RoleGuard.check_access("staff", ["admin", "staff"]) is True

    def test_student_denied(self) -> None:
        with pytest.raises(PermissionError, match="Access Denied"):
            RoleGuard.check_access("student", ["admin", "staff"])

    def test_empty_allowed_roles(self) -> None:
        with pytest.raises(PermissionError):
            RoleGuard.check_access("admin", [])

    def test_single_role_match(self) -> None:
        assert RoleGuard.check_access("student", ["student"]) is True

    def test_single_role_mismatch(self) -> None:
        with pytest.raises(PermissionError):
            RoleGuard.check_access("admin", ["student"])

    def test_case_sensitive(self) -> None:
        with pytest.raises(PermissionError):
            RoleGuard.check_access("Admin", ["admin"])
