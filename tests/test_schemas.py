"""Tests for IMS Pydantic schemas and error codes."""

import os
import sys

import pytest

# config/courses.py uses `from courses_pkg import ...` which needs config/ on the path
_config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
if _config_dir not in sys.path:
    sys.path.insert(0, _config_dir)

from api.schemas import (
    ErrorCode,
    LoginRequest,
    StudentCreate,
    CourseCreate,
    AttendanceRecord,
    PaymentCreate,
    StaffCreate,
    PlacementCreate,
    error_code_for_status,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_all_codes_exist(self) -> None:
        assert ErrorCode.VALIDATION_ERROR.value == "validation_error"
        assert ErrorCode.BAD_REQUEST.value == "bad_request"
        assert ErrorCode.UNAUTHORIZED.value == "unauthorized"
        assert ErrorCode.FORBIDDEN.value == "forbidden"
        assert ErrorCode.NOT_FOUND.value == "not_found"
        assert ErrorCode.CONFLICT.value == "conflict"
        assert ErrorCode.RATE_LIMITED.value == "rate_limited"


class TestErrorCodeForStatus:
    """Tests for error_code_for_status helper."""

    def test_known_status(self) -> None:
        assert error_code_for_status(400) == "bad_request"
        assert error_code_for_status(404) == "not_found"

    def test_unknown_status(self) -> None:
        assert error_code_for_status(999) == "internal_server_error"

    def test_500(self) -> None:
        assert error_code_for_status(500) == "internal_server_error"


class TestLoginRequest:
    """Tests for LoginRequest schema."""

    def test_valid_login(self) -> None:
        req = LoginRequest(username="testuser", password="Pass1234")
        assert req.username == "testuser"


class TestStudentCreate:
    """Tests for StudentCreate schema."""

    def test_valid_student(self) -> None:
        student = StudentCreate(
            first_name="John",
            last_name="Doe",
            email="john@ims.edu",
            phone="9876543210",
            dob="2000-01-15",
            gender="Male",
            course_id=1,
            session_id=1,
        )
        assert student.first_name == "John"

    def test_missing_required(self) -> None:
        with pytest.raises(Exception):
            StudentCreate(first_name="John")


class TestCourseCreate:
    """Tests for CourseCreate schema."""

    def test_valid_course(self) -> None:
        course = CourseCreate(
            code="CS201",
            name="Data Structures",
            duration_months=6,
            fee=25000.0,
        )
        assert course.name == "Data Structures"

    def test_missing_required(self) -> None:
        with pytest.raises(Exception):
            CourseCreate(name="Data Structures")


class TestAttendanceRecord:
    """Tests for AttendanceRecord schema."""

    def test_valid_attendance(self) -> None:
        att = AttendanceRecord(
            student_id=1,
            subject_id=1,
            session_id=1,
            date="2025-01-15",
            status="present",
        )
        assert att.status == "present"


class TestPaymentCreate:
    """Tests for PaymentCreate schema."""

    def test_valid_payment(self) -> None:
        payment = PaymentCreate(
            fee_id=1,
            amount=50000.0,
            mode="bank_transfer",
            transaction_id="TXN001",
        )
        assert payment.amount == 50000.0

    def test_default_mode(self) -> None:
        payment = PaymentCreate(fee_id=1, amount=1000.0)
        assert payment.mode == "Cash"


class TestStaffCreate:
    """Tests for StaffCreate schema."""

    def test_valid_staff(self) -> None:
        staff = StaffCreate(
            first_name="Jane",
            last_name="Smith",
            email="jane@ims.edu",
            join_date="2025-01-15",
        )
        assert staff.first_name == "Jane"

    def test_missing_required(self) -> None:
        with pytest.raises(Exception):
            StaffCreate(first_name="Jane")


class TestPlacementCreate:
    """Tests for PlacementCreate schema."""

    def test_valid_placement(self) -> None:
        placement = PlacementCreate(
            student_id=1,
            company_name="TechCorp",
            job_title="Software Engineer",
            package_lpa=12.5,
            offer_date="2025-06-01",
        )
        assert placement.package_lpa == 12.5
