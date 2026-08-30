"""Tests for LeaveService."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import Course, LeaveStatus, Session, Staff, Student, User, UserRole
from services.leave_service import LeaveService




pytestmark = pytest.mark.slow
@pytest.fixture
def db_session() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def seeded_db(db_session) -> tuple[object, ...]:
    # Create admin user
    admin = User(
        username="admin_leave",
        password_hash="hash",
        role=UserRole.admin,
        email="admin@bb.edu.in",
    )
    db_session.add(admin)

    # Create student user + profile
    stu_user = User(
        username="stu_leave",
        password_hash="hash",
        role=UserRole.student,
        email="stu@bb.edu.in",
    )
    db_session.add(stu_user)
    db_session.flush()
    course = Course(code="CS101", name="CS", duration_months=6, fee=10000)
    db_session.add(course)
    sess = Session(name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    db_session.add(sess)
    db_session.flush()
    student = Student(
        user_id=stu_user.id,
        enrollment_no="BB0001",
        first_name="Leave",
        last_name="Student",
        dob=date(2000, 1, 1),
        course_id=course.id,
        session_id=sess.id,
        admission_date=date(2024, 6, 1),
    )
    db_session.add(student)

    # Create staff user + profile
    stf_user = User(
        username="stf_leave",
        password_hash="hash",
        role=UserRole.staff,
        email="stf@bb.edu.in",
    )
    db_session.add(stf_user)
    db_session.flush()
    staff = Staff(
        user_id=stf_user.id,
        first_name="Staff",
        last_name="Leave",
        department="IT",
        designation="Lecturer",
        join_date=date(2023, 1, 1),
    )
    db_session.add(staff)
    db_session.commit()
    return db_session, admin, student, staff, sess


class TestLeaveService:
    def test_apply_student_leave(self, seeded_db) -> None:
        db, admin, student, staff, sess = seeded_db
        service = LeaveService(db)
        result = service.apply_leave(
            {
                "student_id": student.id,
                "start_date": date(2024, 10, 1),
                "end_date": date(2024, 10, 3),
                "reason": "Medical emergency",
            }
        )
        assert result["reason"] == "Medical emergency"
        assert result["status"] == "pending"
        assert "Leave Student" in result["applicant"]

    def test_apply_staff_leave(self, seeded_db) -> None:
        db, admin, student, staff, sess = seeded_db
        service = LeaveService(db)
        result = service.apply_leave(
            {
                "staff_id": staff.id,
                "start_date": date(2024, 11, 1),
                "end_date": date(2024, 11, 2),
                "reason": "Personal work",
            }
        )
        assert result["status"] == "pending"
        assert "Staff Leave" in result["applicant"]

    def test_get_leaves_for_student(self, seeded_db) -> None:
        db, admin, student, staff, sess = seeded_db
        service = LeaveService(db)
        service.apply_leave(
            {
                "student_id": student.id,
                "start_date": date(2024, 10, 1),
                "end_date": date(2024, 10, 3),
                "reason": "Sick",
            }
        )

        leaves = service.get_leaves_for_user(student_id=student.id)
        assert len(leaves) == 1

    def test_approve_leave(self, seeded_db) -> None:
        db, admin, student, staff, sess = seeded_db
        service = LeaveService(db)
        result = service.apply_leave(
            {
                "student_id": student.id,
                "start_date": date(2024, 10, 1),
                "end_date": date(2024, 10, 3),
                "reason": "Sick",
            }
        )

        approved = service.approve_leave(result["id"], admin.id)
        assert approved["status"] == "approved"

    def test_reject_leave(self, seeded_db) -> None:
        db, admin, student, staff, sess = seeded_db
        service = LeaveService(db)
        result = service.apply_leave(
            {
                "student_id": student.id,
                "start_date": date(2024, 10, 1),
                "end_date": date(2024, 10, 3),
                "reason": "Sick",
            }
        )

        rejected = service.reject_leave(result["id"], admin.id)
        assert rejected["status"] == "rejected"

    def test_get_all_leaves(self, seeded_db) -> None:
        db, admin, student, staff, sess = seeded_db
        service = LeaveService(db)
        service.apply_leave(
            {
                "student_id": student.id,
                "start_date": date(2024, 10, 1),
                "end_date": date(2024, 10, 3),
                "reason": "Sick",
            }
        )

        leaves = service.get_all_leaves()
        assert len(leaves) == 1

    def test_get_all_leaves_by_status(self, seeded_db) -> None:
        db, admin, student, staff, sess = seeded_db
        service = LeaveService(db)
        _ = service.apply_leave(
            {
                "student_id": student.id,
                "start_date": date(2024, 10, 1),
                "end_date": date(2024, 10, 3),
                "reason": "Sick",
            }
        )

        pending = service.get_all_leaves(status=LeaveStatus.pending)
        assert len(pending) == 1

        approved = service.get_all_leaves(status=LeaveStatus.approved)
        assert len(approved) == 0
