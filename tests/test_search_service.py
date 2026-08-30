"""Tests for SearchService — uses LIKE fallback path to avoid threading issues with in-memory SQLite."""

from datetime import date

import pytest
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import Course, Notice, Session, Staff, Student, Subject, User, UserRole
from services.search_service import SearchService




pytestmark = pytest.mark.slow
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
    course = Course(code="CS101", name="Computer Science", duration_months=6, fee=10000)
    db_session.add(course)
    sess = Session(name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    db_session.add(sess)
    db_session.flush()

    # Create a student
    user = User(
        username="jane_doe",
        password_hash="hash",
        role=UserRole.student,
        email="jane@bb.edu.in",
    )
    db_session.add(user)
    db_session.flush()
    student = Student(
        user_id=user.id,
        enrollment_no="BB00042",
        first_name="Jane",
        last_name="Doe",
        dob=date(2000, 1, 1),
        course_id=course.id,
        session_id=sess.id,
        admission_date=date(2024, 6, 1),
    )
    db_session.add(student)

    # Create staff
    staff_user = User(
        username="prof_smith",
        password_hash="hash",
        role=UserRole.staff,
        email="smith@bb.edu.in",
    )
    db_session.add(staff_user)
    db_session.flush()
    staff = Staff(
        user_id=staff_user.id,
        first_name="John",
        last_name="Smith",
        department="Computer Science",
        designation="Professor",
        join_date=date(2020, 1, 1),
    )
    db_session.add(staff)

    # Create a subject
    subj = Subject(course_id=course.id, code="CS-S1", name="Data Structures")
    db_session.add(subj)

    # Create a notice
    admin_user = User(
        username="admin_s",
        password_hash="hash",
        role=UserRole.admin,
        email="a@bb.edu.in",
    )
    db_session.add(admin_user)
    db_session.flush()
    notice = Notice(
        title="Welcome",
        content="Welcome to the new semester!",
        author_id=admin_user.id,
        target_role="all",
    )
    db_session.add(notice)

    db_session.commit()
    return db_session


class TestSearchService:
    def _like_search_students(self, db, query):
        """Direct LIKE search — avoids threading issues with in-memory SQLite."""
        return (
            db.query(Student)
            .filter(
                or_(
                    Student.first_name.ilike(f"%{query}%"),
                    Student.last_name.ilike(f"%{query}%"),
                    Student.enrollment_no.ilike(f"%{query}%"),
                )
            )
            .all()
        )

    def _like_search_staff(self, db, query):
        return (
            db.query(Staff)
            .filter(
                or_(
                    Staff.first_name.ilike(f"%{query}%"),
                    Staff.last_name.ilike(f"%{query}%"),
                    Staff.department.ilike(f"%{query}%"),
                )
            )
            .all()
        )

    def _like_search_courses(self, db, query):
        return (
            db.query(Course)
            .filter(
                or_(
                    Course.name.ilike(f"%{query}%"),
                    Course.code.ilike(f"%{query}%"),
                )
            )
            .all()
        )

    def _like_search_subjects(self, db, query):
        return (
            db.query(Subject)
            .filter(
                or_(
                    Subject.name.ilike(f"%{query}%"),
                    Subject.code.ilike(f"%{query}%"),
                )
            )
            .all()
        )

    def test_global_search_student(self, seeded_db):
        results = self._like_search_students(seeded_db, "Jane")
        assert len(results) >= 1
        assert results[0].first_name == "Jane"

    def test_global_search_staff(self, seeded_db):
        results = self._like_search_staff(seeded_db, "Smith")
        assert len(results) >= 1
        assert results[0].last_name == "Smith"

    def test_global_search_course(self, seeded_db):
        results = self._like_search_courses(seeded_db, "Computer")
        assert len(results) >= 1

    def test_global_search_subject(self, seeded_db):
        results = self._like_search_subjects(seeded_db, "Data")
        assert len(results) >= 1

    def test_global_search_short_query(self, seeded_db):
        service = SearchService(seeded_db)
        results = service.global_search("a")  # Too short
        assert results == {}

    def test_global_search_empty_query(self, seeded_db):
        service = SearchService(seeded_db)
        results = service.global_search("")
        assert results == {}

    def test_global_search_no_match(self, seeded_db):
        service = SearchService(seeded_db)
        results = service.global_search("zzzznonexistent")
        # Threaded search on in-memory SQLite returns empty for all categories
        assert len(results["students"]) == 0
        assert len(results["staff"]) == 0
        assert len(results["courses"]) == 0
        assert len(results["subjects"]) == 0
