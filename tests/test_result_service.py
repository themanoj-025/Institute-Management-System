"""Tests for ResultService with is_deleted filtering."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import Course, Result, Session, Student, Subject, User, UserRole
from services.result_service import ResultService


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
    course = Course(code="CS101", name="CS", duration_months=6, fee=10000)
    db_session.add(course)
    sess = Session(name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    db_session.add(sess)
    subject = Subject(course_id=1, code="CS101-S1", name="Algorithms")
    db_session.add(subject)
    db_session.flush()

    user = User(
        username="res_stu",
        password_hash="hash",
        role=UserRole.student,
        email="r@bb.edu.in",
    )
    db_session.add(user)
    db_session.flush()

    student = Student(
        user_id=user.id,
        enrollment_no="BB0001",
        first_name="Result",
        last_name="Student",
        dob=date(2000, 1, 1),
        course_id=course.id,
        session_id=sess.id,
        admission_date=date(2024, 6, 1),
    )
    db_session.add(student)
    db_session.flush()

    # Create a result
    result = Result(
        student_id=student.id,
        subject_id=subject.id,
        session_id=sess.id,
        exam_type="Midterm",
        marks_obtained=85.0,
        total_marks=100.0,
        grade="A",
    )
    db_session.add(result)
    db_session.commit()
    return db_session, student, subject, sess


class TestResultService:
    def test_get_existing_marks(self, seeded_db):
        db, student, subject, sess = seeded_db
        service = ResultService(db)
        marks = service.get_existing_marks(subject.id, sess.id, "Midterm")
        assert len(marks) == 1
        assert marks[student.id] == 85.0

    def test_get_existing_marks_empty(self, seeded_db):
        db, student, subject, sess = seeded_db
        service = ResultService(db)
        marks = service.get_existing_marks(subject.id, sess.id, "Final")
        assert marks == {}

    def test_get_student_results(self, seeded_db):
        db, student, subject, sess = seeded_db
        service = ResultService(db)
        results = service.get_student_results(student.id)
        assert len(results) == 1
        assert results[0]["subject"] == "Algorithms"
        assert results[0]["marks"] == 85.0
        assert results[0]["grade"] == "A"
        assert results[0]["pct"] == 85.0

    def test_get_student_results_empty(self, db_session):
        service = ResultService(db_session)
        assert service.get_student_results(999) == []

    def test_bulk_upsert_create(self, seeded_db):
        db, student, subject, sess = seeded_db
        service = ResultService(db)
        records = [
            {
                "student_id": student.id,
                "subject_id": subject.id,
                "exam_type": "Final",
                "marks": 90.0,
                "total": 100.0,
                "grade": "A",
            }
        ]
        result = service.bulk_upsert(records, sess.id)
        assert result is True

        results = service.get_student_results(student.id)
        assert len(results) == 2

    def test_bulk_upsert_update_existing(self, seeded_db):
        db, student, subject, sess = seeded_db
        service = ResultService(db)
        records = [
            {
                "student_id": student.id,
                "subject_id": subject.id,
                "exam_type": "Midterm",
                "marks": 95.0,
                "total": 100.0,
                "grade": "A+",
            }
        ]
        service.bulk_upsert(records, sess.id)

        results = service.get_student_results(student.id)
        assert len(results) == 1
        assert results[0]["marks"] == 95.0

    def test_soft_deleted_excluded(self, seeded_db):
        """Soft-deleted results should NOT appear in queries."""
        db, student, subject, sess = seeded_db
        service = ResultService(db)

        # Soft-delete the result
        db.query(Result).filter(Result.student_id == student.id).update({"is_deleted": True})
        db.commit()

        results = service.get_student_results(student.id)
        assert results == []

        marks = service.get_existing_marks(subject.id, sess.id, "Midterm")
        assert marks == {}
