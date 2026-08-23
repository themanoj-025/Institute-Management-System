"""Tests for AttendanceService."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import (
    Attendance,
    AttendanceStatus,
    Course,
    Session,
    Student,
    Subject,
    User,
    UserRole,
)
from services.attendance_service import AttendanceService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def seeded_db(db_session):
    """Create minimal seed data for attendance tests."""
    course = Course(code="CS101", name="CS Basics", duration_months=6, fee=10000)
    db_session.add(course)
    sess = Session(name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    db_session.add(sess)
    subject = Subject(course_id=1, code="CS101-S1", name="Programming 101", staff_id=None)
    db_session.add(subject)

    users = []
    students = []
    for i in range(3):
        u = User(
            username=f"stu{i}",
            password_hash="hash",
            role=UserRole.student,
            email=f"s{i}@bb.edu.in",
        )
        db_session.add(u)
        db_session.flush()
        s = Student(
            user_id=u.id,
            enrollment_no=f"BB{i + 1:05d}",
            first_name=f"Student{i}",
            last_name="Test",
            dob=date(2000, 1, 1),
            course_id=course.id,
            session_id=sess.id,
            admission_date=date(2024, 6, 1),
        )
        db_session.add(s)
        users.append(u)
        students.append(s)

    db_session.commit()
    return db_session, sess, subject, students


class TestAttendanceService:
    def test_get_by_date_subject(self, seeded_db):
        db, sess, subject, students = seeded_db
        service = AttendanceService(db)

        # Create some attendance records
        for i, student in enumerate(students):
            status = AttendanceStatus.present if i % 2 == 0 else AttendanceStatus.absent
            db.add(
                Attendance(
                    student_id=student.id,
                    subject_id=subject.id,
                    session_id=sess.id,
                    date=date(2024, 9, 1),
                    status=status,
                )
            )
        db.commit()

        result = service.get_by_date_subject(date(2024, 9, 1), subject.id)
        assert len(result) == 3
        assert result[students[0].id].value == "present"

    def test_get_by_date_subject_empty(self, seeded_db):
        db, sess, subject, students = seeded_db
        service = AttendanceService(db)

        result = service.get_by_date_subject(date(2024, 1, 1), subject.id)
        assert result == {}

    def test_bulk_upsert_create(self, seeded_db):
        db, sess, subject, students = seeded_db
        service = AttendanceService(db)

        records = [
            {
                "student_id": s.id,
                "subject_id": subject.id,
                "date": "2024-09-01",
                "status": "present",
            }
            for s in students
        ]
        result = service.bulk_upsert(records, staff_id=1)
        assert result is True

        count = db.query(Attendance).count()
        assert count == 3

    def test_bulk_upsert_update_existing(self, seeded_db):
        db, sess, subject, students = seeded_db
        service = AttendanceService(db)

        # Create initial record
        db.add(
            Attendance(
                student_id=students[0].id,
                subject_id=subject.id,
                session_id=sess.id,
                date=date(2024, 9, 1),
                status=AttendanceStatus.present,
            )
        )
        db.commit()

        # Update it via bulk_upsert
        records = [
            {
                "student_id": students[0].id,
                "subject_id": subject.id,
                "date": "2024-09-01",
                "status": "absent",
            }
        ]
        service.bulk_upsert(records, staff_id=1)

        updated = db.query(Attendance).filter(Attendance.student_id == students[0].id).first()
        assert updated.status == AttendanceStatus.absent

    def test_bulk_upsert_duplicate(self, seeded_db):
        db, sess, subject, students = seeded_db
        service = AttendanceService(db)

        # Same record inserted twice should result in one row (update)
        records = [
            {
                "student_id": students[0].id,
                "subject_id": subject.id,
                "date": "2024-09-01",
                "status": "present",
            },
        ]
        service.bulk_upsert(records, staff_id=1)
        service.bulk_upsert(records, staff_id=1)

        count = db.query(Attendance).count()
        assert count == 1
