"""Tests for PlacementService."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import Course, Session, Student, User, UserRole
from services.placement_service import PlacementService

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
    course = Course(code="CS101", name="CS", duration_months=6, fee=10000)
    db_session.add(course)
    sess = Session(name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    db_session.add(sess)
    db_session.flush()

    user = User(
        username="placed_stu",
        password_hash="hash",
        role=UserRole.student,
        email="p@bb.edu.in",
    )
    db_session.add(user)
    db_session.flush()

    student = Student(
        user_id=user.id,
        enrollment_no="BB0001",
        first_name="Placed",
        last_name="Student",
        dob=date(2000, 1, 1),
        course_id=course.id,
        session_id=sess.id,
        admission_date=date(2024, 6, 1),
    )
    db_session.add(student)
    db_session.commit()
    return db_session, student


class TestPlacementService:
    def test_create_placement(self, seeded_db) -> None:
        db, student = seeded_db
        service = PlacementService(db)
        result = service.create_placement(
            student_id=student.id,
            company_name="Google",
            job_title="SDE",
            package_lpa=24.0,
            offer_date=date(2024, 9, 15),
        )
        assert result["company_name"] == "Google"
        assert result["job_title"] == "SDE"
        assert result["package_lpa"] == 24.0
        assert "Placed Student" in result["student_name"]

    def test_get_all_placements(self, seeded_db) -> None:
        db, student = seeded_db
        service = PlacementService(db)
        service.create_placement(
            student_id=student.id,
            company_name="Google",
            job_title="SDE",
            package_lpa=24.0,
            offer_date=date(2024, 9, 15),
        )
        service.create_placement(
            student_id=student.id,
            company_name="Microsoft",
            job_title="SWE",
            package_lpa=20.0,
            offer_date=date(2024, 10, 1),
        )

        placements = service.get_all_placements()
        assert len(placements) == 2

    def test_placement_order(self, seeded_db) -> None:
        db, student = seeded_db
        service = PlacementService(db)
        service.create_placement(
            student_id=student.id,
            company_name="A",
            job_title="Dev",
            package_lpa=10.0,
            offer_date=date(2024, 1, 1),
        )
        service.create_placement(
            student_id=student.id,
            company_name="B",
            job_title="Dev",
            package_lpa=15.0,
            offer_date=date(2024, 2, 1),
        )

        placements = service.get_all_placements()
        assert placements[0]["id"] > placements[1]["id"]  # Desc order

    def test_empty_placements(self, db_session) -> None:
        service = PlacementService(db_session)
        assert service.get_all_placements() == []
