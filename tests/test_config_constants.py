"""Tests for IMS configuration constants."""

import pytest

from config.constants import (
    ANIMATION_DELAY,
    ANIMATION_STEPS,
    APP_NAME,
    APP_VERSION,
    ATTENDANCE_ABSENT,
    ATTENDANCE_EXCUSED,
    ATTENDANCE_LATE,
    ATTENDANCE_PRESENT,
    BASE_DIR,
    COMPANY_NAME,
    EXAM_TYPES,
    FEE_PAID,
    FEE_UNPAID,
    LEAVE_APPROVED,
    LEAVE_PENDING,
    LEAVE_REJECTED,
    ROLE_ADMIN,
    ROLE_STAFF,
    ROLE_STUDENT,
    ROLES,
    SIDEBAR_WIDTH_COLLAPSED,
    SIDEBAR_WIDTH_EXPANDED,
    STATUS_ACTIVE,
    STATUS_INACTIVE,
)


class TestAppInfo:
    """Tests for application information constants."""

    def test_app_name(self) -> None:
        assert isinstance(APP_NAME, str)
        assert len(APP_NAME) > 0

    def test_app_version(self) -> None:
        assert isinstance(APP_VERSION, str)
        assert "." in APP_VERSION

    def test_company_name(self) -> None:
        assert isinstance(COMPANY_NAME, str)


class TestRoles:
    """Tests for role constants."""

    def test_roles_list(self) -> None:
        assert ROLE_ADMIN in ROLES
        assert ROLE_STAFF in ROLES
        assert ROLE_STUDENT in ROLES

    def test_role_values(self) -> None:
        assert ROLE_ADMIN == "admin"
        assert ROLE_STAFF == "staff"
        assert ROLE_STUDENT == "student"

    def test_three_roles(self) -> None:
        assert len(ROLES) == 3


class TestStatuses:
    """Tests for status constants."""

    def test_status_values(self) -> None:
        assert STATUS_ACTIVE == "active"
        assert STATUS_INACTIVE == "inactive"


class TestUIConstants:
    """Tests for UI constants."""

    def test_sidebar_widths(self) -> None:
        assert SIDEBAR_WIDTH_EXPANDED > SIDEBAR_WIDTH_COLLAPSED
        assert SIDEBAR_WIDTH_EXPANDED > 0
        assert SIDEBAR_WIDTH_COLLAPSED > 0

    def test_animation(self) -> None:
        assert ANIMATION_STEPS > 0
        assert ANIMATION_DELAY > 0


class TestAcademicConstants:
    """Tests for academic-related constants."""

    def test_attendance_statuses(self) -> None:
        assert ATTENDANCE_PRESENT == "present"
        assert ATTENDANCE_ABSENT == "absent"
        assert ATTENDANCE_LATE == "late"
        assert ATTENDANCE_EXCUSED == "excused"

    def test_exam_types(self) -> None:
        assert isinstance(EXAM_TYPES, list)
        assert len(EXAM_TYPES) >= 3

    def test_fee_statuses(self) -> None:
        assert FEE_PAID == "paid"
        assert FEE_UNPAID == "unpaid"

    def test_leave_statuses(self) -> None:
        assert LEAVE_PENDING == "pending"
        assert LEAVE_APPROVED == "approved"
        assert LEAVE_REJECTED == "rejected"

    def test_base_dir(self) -> None:
        assert BASE_DIR.exists()
