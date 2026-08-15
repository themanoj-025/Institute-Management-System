"""Tests for StaffService."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import Staff, User, UserRole
from services.staff_service import StaffService


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
    for i in range(3):
        user = User(
            username=f"staff{i}",
            password_hash="hash",
            role=UserRole.staff,
            email=f"staff{i}@bb.edu.in",
        )
        db_session.add(user)
        db_session.flush()
        staff = Staff(
            user_id=user.id,
            first_name=f"First{i}",
            last_name=f"Last{i}",
            department="IT" if i % 2 == 0 else "CS",
            designation="Lecturer",
            join_date=date(2020, 1, 1 + i),
            salary=50000.0 + i * 10000,
        )
        db_session.add(staff)
    db_session.commit()
    return db_session


class TestStaffService:
    def test_get_all_staff(self, seeded_db):
        service = StaffService(seeded_db)
        result = service.get_all_staff()
        assert result["total"] >= 3
        assert len(result["staff"]) >= 3
        assert result["staff"][0]["first_name"] == "First2"  # desc order

    def test_get_all_staff_paginated(self, seeded_db):
        service = StaffService(seeded_db)
        result = service.get_all_staff(limit=2, offset=0)
        assert len(result["staff"]) == 2
        assert result["total"] >= 3

    def test_get_all_staff_search(self, seeded_db):
        service = StaffService(seeded_db)
        result = service.get_all_staff(search_query="First0")
        assert len(result["staff"]) == 1
        assert result["staff"][0]["first_name"] == "First0"

    def test_get_all_staff_search_partial(self, seeded_db):
        service = StaffService(seeded_db)
        result = service.get_all_staff(search_query="First")
        assert result["total"] >= 3

    def test_get_staff_by_id(self, seeded_db):
        service = StaffService(seeded_db)
        staff = service.get_staff_by_id(1)
        assert staff["id"] == 1
        assert "full_name" in staff

    def test_get_staff_by_id_not_found(self, seeded_db):
        service = StaffService(seeded_db)
        with pytest.raises(ValueError, match="Staff not found"):
            service.get_staff_by_id(999)

    def test_create_staff(self, db_session):
        service = StaffService(db_session)
        result = service.create_staff(
            {
                "username": "new_staff",
                "email": "new@bb.edu.in",
                "first_name": "New",
                "last_name": "Staff",
                "department": "Math",
                "designation": "Assistant Professor",
                "join_date": date(2024, 1, 1),
                "salary": 60000.0,
            }
        )
        assert result["first_name"] == "New"
        assert result["full_name"] == "New Staff"
        assert result["username"] == "new_staff"

        # Verify user was created
        user = db_session.query(User).filter(User.username == "new_staff").first()
        assert user is not None
        assert user.role == UserRole.staff

    def test_get_all_staff_empty(self, db_session):
        service = StaffService(db_session)
        result = service.get_all_staff()
        assert result["total"] == 0
        assert result["staff"] == []
