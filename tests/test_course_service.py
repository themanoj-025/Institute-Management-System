"""Tests for CourseService."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import Course, CourseModule, Subject
from services.course_service import CourseService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def seeded_db(db_session):
    course = Course(
        code="PY101",
        name="Python Basics",
        duration_months=3,
        fee=15000,
        description="Learn Python",
    )
    db_session.add(course)
    db_session.flush()

    for i in range(2):
        db_session.add(CourseModule(course_id=course.id, name=f"Module {i + 1}", order=i + 1))
        db_session.add(Subject(course_id=course.id, code=f"PY-S{i + 1}", name=f"Subject {i + 1}"))
    db_session.commit()
    return db_session


class TestCourseService:
    def test_get_all_courses(self, seeded_db):
        service = CourseService(seeded_db)
        courses = service.get_all_courses()
        assert len(courses) == 1
        assert courses[0]["code"] == "PY101"
        assert courses[0]["name"] == "Python Basics"

    def test_get_all_courses_empty(self, db_session):
        service = CourseService(db_session)
        courses = service.get_all_courses()
        assert courses == []

    def test_get_course_details(self, seeded_db):
        service = CourseService(seeded_db)
        details = service.get_course_details(1)
        assert details["code"] == "PY101"
        assert len(details["modules"]) == 2
        assert len(details["subjects"]) == 2
        assert details["modules"][0]["name"] == "Module 1"

    def test_get_course_details_not_found(self, seeded_db):
        service = CourseService(seeded_db)
        with pytest.raises(ValueError, match="Course not found"):
            service.get_course_details(999)

    def test_get_course_details_includes_duration(self, seeded_db):
        service = CourseService(seeded_db)
        details = service.get_course_details(1)
        assert details["duration"] == 3
        assert details["fee"] == 15000
        assert details["description"] == "Learn Python"
