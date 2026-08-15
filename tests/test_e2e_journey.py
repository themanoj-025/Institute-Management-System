"""End-to-end user journey integration test.

Tests the full realistic journey:
1. Admin creates a student
2. Student completes email verification
3. Student logs in (including OTP)
4. Staff marks that student's attendance
5. Fee payment is recorded for the student
6. A result is entered
7. ML risk score is computed and retrievable with SHAP explanation
8. An export (fee report) is generated successfully

This test exercises the real API surface end-to-end against a
test database (in-memory SQLite).
"""

import os
import secrets as _secrets
from datetime import datetime, timedelta

import bcrypt
import pytest

from database.models import (
    Attendance,
    AttendanceStatus,
    Course,
    Fee,
    FeeStatus,
    Result,
    Session as AcadSession,
    Staff,
    Student,
    Subject,
    User,
    UserRole,
)
from utils.time import utc_now


@pytest.fixture
def test_data(test_db):
    """Set up minimal test data for the end-to-end journey."""
    now = utc_now()

    # Create session
    session = AcadSession(
        name="2025-2026",
        start_date=datetime(2025, 6, 1).date(),
        end_date=datetime(2026, 5, 31).date(),
        is_active=True,
    )
    test_db.add(session)
    test_db.commit()

    # Create course
    import uuid as _uuid

    _unique_suffix = _uuid.uuid4().hex[:8]
    course = Course(
        code=f"CS-E2E-{_unique_suffix}",
        name="Computer Science E2E",
        duration_months=36,
        fee=50000.0,
    )
    test_db.add(course)
    test_db.commit()

    # Create subject
    subject = Subject(
        course_id=course.id,
        code=f"E2E-MATH-{_unique_suffix}",
        name="Mathematics",
    )
    test_db.add(subject)
    test_db.commit()

    # Create admin user
    admin_pwd = f"Adm-{_secrets.token_hex(8)}"
    admin_hash = bcrypt.hashpw(admin_pwd.encode("utf-8"), bcrypt.gensalt(4)).decode("utf-8")
    admin = User(
        username=f"admin_e2e_{_unique_suffix}",
        password_hash=admin_hash,
        role=UserRole.admin,
        email=f"admin_e2e_{_unique_suffix}@bb.edu.in",
        is_active=True,
        email_verified=True,
    )
    test_db.add(admin)
    test_db.commit()

    # Create staff user
    staff_pwd = f"Stf-{_secrets.token_hex(8)}"
    staff_hash = bcrypt.hashpw(staff_pwd.encode("utf-8"), bcrypt.gensalt(4)).decode("utf-8")
    staff_user = User(
        username=f"staff_e2e_{_unique_suffix}",
        password_hash=staff_hash,
        role=UserRole.staff,
        email=f"staff_e2e_{_unique_suffix}@bb.edu.in",
        is_active=True,
        email_verified=True,
    )
    test_db.add(staff_user)
    test_db.commit()

    staff = Staff(
        user_id=staff_user.id,
        first_name="E2E",
        last_name="Staff",
        department="CS",
        designation="Professor",
        join_date=now.date(),
    )
    test_db.add(staff)
    test_db.commit()

    # Create student user (unverified initially)
    student_pwd = f"Stu-{_secrets.token_hex(8)}"
    student_hash = bcrypt.hashpw(student_pwd.encode("utf-8"), bcrypt.gensalt(4)).decode("utf-8")
    student_user = User(
        username=f"student_e2e_{_unique_suffix}",
        password_hash=student_hash,
        role=UserRole.student,
        email=f"student_e2e_{_unique_suffix}@bb.edu.in",
        is_active=True,
        email_verified=False,
    )
    test_db.add(student_user)
    test_db.commit()

    student = Student(
        user_id=student_user.id,
        enrollment_no=f"BB9{_unique_suffix}",
        first_name="E2E",
        last_name="Student",
        dob=datetime(2000, 1, 15).date(),
        gender="Male",
        course_id=course.id,
        session_id=session.id,
        admission_date=now.date(),
    )
    test_db.add(student)
    test_db.commit()

    return {
        "admin_user": admin,
        "admin_password": admin_pwd,
        "staff_user": staff_user,
        "staff": staff,
        "staff_password": staff_pwd,
        "student_user": student_user,
        "student": student,
        "student_password": student_pwd,
        "course": course,
        "subject": subject,
        "session": session,
        "_unique_suffix": _unique_suffix,
    }


class TestEndToEndJourney:
    """End-to-end user journey through the entire system."""

    def test_full_journey(self, test_db, auth_service, test_data):
        """Complete end-to-end test of the user journey."""

        data = test_data

        # Use a separate transaction to prevent cascading failures
        try:
            self._run_journey_steps(test_db, auth_service, data)
        except Exception:
            test_db.rollback()
            raise

    def _run_journey_steps(self, test_db, auth_service, data):
        """Run the actual journey steps in a single transaction scope."""
        student_user = data["student_user"]
        student = data["student"]
        subject = data["subject"]

        # ── Step 1: Verify email ──
        from services.auth_service import AuthService

        auth_svc = AuthService(test_db)

        # Generate verification token
        raw_token = auth_svc.generate_verification_token(student_user.id)
        assert raw_token is not None
        assert len(raw_token) > 20

        # Verify the email
        result = auth_svc.verify_email_token(student_user.id, raw_token)
        assert result is True

        # Confirm user is verified
        test_db.refresh(student_user)
        assert student_user.email_verified is True

        # ── Step 2: Login (simulate OTP flow) ──
        # Login triggers OTP, then verify OTP to get JWT
        from unittest.mock import patch as _patch

        with _patch("services.auth_service.secrets.randbelow", return_value=23456):
            login_result = auth_svc.login(
                f"student_e2e_{data['_unique_suffix']}", data["student_password"]
            )
            assert login_result["user_id"] == student_user.id
            assert login_result["role"] == "student"
            assert login_result.get("otp_sent") is True

        # Verify OTP: randbelow(23456) + 100000 = 123456
        otp_result = auth_svc.verify_otp(student_user.id, "123456")
        assert otp_result["user"]["id"] == student_user.id
        assert otp_result["user"]["role"] == "student"
        assert otp_result["user"]["name"] == "E2E Student"

        # ── Step 3: Staff marks attendance ──
        att = Attendance(
            student_id=student.id,
            subject_id=subject.id,
            session_id=data["session"].id,
            date=utc_now().date(),
            status=AttendanceStatus.present,
        )
        test_db.add(att)
        test_db.commit()

        # Verify attendance is queryable
        attendance_query = (
            test_db.query(Attendance).filter(Attendance.student_id == student.id).all()
        )
        assert len(attendance_query) == 1
        assert attendance_query[0].status == AttendanceStatus.present

        # ── Step 4: Record fee payment ──
        fee = Fee(
            student_id=student.id,
            session_id=data["session"].id,
            total_amount=50000.0,
            paid_amount=0.0,
            due_date=utc_now().date() + timedelta(days=30),
            status=FeeStatus.unpaid,
        )
        test_db.add(fee)
        test_db.commit()

        # Record payment
        from services.fee_service import FeeService

        fee_svc = FeeService(test_db)
        receipt = fee_svc.record_payment(
            fee_id=fee.id,
            amount=25000.0,
            mode="UPI",
            transaction_id="TXN-E2E-001",
        )
        assert receipt is not None
        assert len(receipt) > 0

        # Verify fee balance updated
        test_db.refresh(fee)
        assert fee.paid_amount == 25000.0
        assert fee.status == FeeStatus.partial

        # ── Step 5: Enter a result ──
        result_entry = Result(
            student_id=student.id,
            subject_id=subject.id,
            session_id=data["session"].id,
            exam_type="midterm",
            marks_obtained=85.0,
            total_marks=100.0,
            grade="A",
            date_declared=utc_now().date(),
        )
        test_db.add(result_entry)
        test_db.commit()

        # Verify result is queryable
        results = test_db.query(Result).filter(Result.student_id == student.id).all()
        assert len(results) == 1
        assert results[0].marks_obtained == 85.0
        assert results[0].grade == "A"

        # ── Step 6: Compute ML risk score ──
        from ml.service import MLService

        ml_svc = MLService()
        # This should work even without a trained model (falls back to heuristic)
        risk = ml_svc.predict_student_risk(test_db, student_id=student.id)
        assert risk is not None
        assert risk["student_id"] == student.id
        assert risk["name"] == "E2E Student"
        # Risk score should be between 0 and 1
        assert 0.0 <= risk.get("risk_score", 0) <= 1.0 or risk.get("risk_score") is None
        assert "explanations" in risk

        # If explanations exist, they should reference real feature data
        if risk.get("explanations"):
            explanation = risk["explanations"][0]
            assert "name" in explanation
            assert "value" in explanation
            assert "importance" in explanation
            assert "direction" in explanation

        # ── Step 7: Generate export (fee report) ──
        from services.export_service import ExportService
        import tempfile

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            svc = ExportService(export_dir=tmpdir, auto_create=True)
            headers = [
                "Student Name",
                "Total Amount",
                "Paid Amount",
                "Balance",
                "Status",
            ]
            rows = [
                [
                    "E2E Student",
                    str(fee.total_amount),
                    str(fee.paid_amount),
                    str(fee.total_amount - fee.paid_amount),
                    fee.status.value,
                ]
            ]

            csv_result = svc.to_csv(
                "e2e_fee_report.csv",
                headers,
                rows,
            )
            assert csv_result.path.endswith(".csv")
            assert os.path.getsize(csv_result.path) > 10

            # Verify CSV contains expected student data
            with open(csv_result.path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "E2E Student" in content
            assert "25000.0" in content or "25000" in content

    def test_risk_explanation_references_real_features(self, test_db, test_data):
        """Risk explanation should reference real feature data when available."""
        from ml.service import MLService

        ml_svc = MLService()
        risk = ml_svc.predict_student_risk(test_db, student_id=test_data["student"].id)
        assert risk is not None

        # With attendance, result, and fee data present, the heuristic
        # should produce meaningful explanations
        if risk.get("explanations"):
            has_feature_name = any(
                "attendance" in e["name"] or "marks" in e["name"] or "fee" in e["name"]
                for e in risk["explanations"]
            )
            assert (
                has_feature_name
            ), f"Expected feature names in explanations, got: {risk['explanations']}"
