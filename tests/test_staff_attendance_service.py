"""Tests for StaffAttendanceService."""

from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import Staff, StaffAttendance, AttendanceStatus, User, UserRole
from services.staff_attendance_service import StaffAttendanceService


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
    user = User(
        username="prof1",
        password_hash="hash",
        role=UserRole.staff,
        email="prof@bb.edu.in",
    )
    db_session.add(user)
    db_session.flush()
    staff = Staff(
        user_id=user.id,
        first_name="Prof",
        last_name="One",
        department="CS",
        designation="Professor",
        join_date=date(2020, 1, 1),
    )
    db_session.add(staff)
    db_session.commit()
    return db_session, staff


class TestStaffAttendanceService:
    def test_mark_attendance_create(self, seeded_db):
        db, staff = seeded_db
        service = StaffAttendanceService(db)
        result = service.mark_attendance(
            staff_id=staff.id,
            date=date(2024, 9, 1),
            status=AttendanceStatus.present,
            in_time=time(9, 0),
            out_time=time(17, 0),
        )
        assert result["status"] == "present"
        assert result["in_time"] == "09:00"
        assert result["out_time"] == "17:00"

    def test_mark_attendance_update(self, seeded_db):
        db, staff = seeded_db
        service = StaffAttendanceService(db)
        service.mark_attendance(staff.id, date(2024, 9, 1), AttendanceStatus.present)

        # Update same day
        result = service.mark_attendance(
            staff.id,
            date(2024, 9, 1),
            AttendanceStatus.absent,
        )
        assert result["status"] == "absent"

        # Should be only one record
        count = db.query(StaffAttendance).filter(StaffAttendance.staff_id == staff.id).count()
        assert count == 1

    def test_mark_attendance_without_times(self, seeded_db):
        db, staff = seeded_db
        service = StaffAttendanceService(db)
        result = service.mark_attendance(staff.id, date(2024, 9, 1), AttendanceStatus.late)
        assert result["status"] == "late"
        assert result["in_time"] is None

    def test_get_staff_attendance(self, seeded_db):
        db, staff = seeded_db
        service = StaffAttendanceService(db)
        for day in range(1, 6):
            service.mark_attendance(staff.id, date(2024, 9, day), AttendanceStatus.present)

        records = service.get_staff_attendance(staff.id)
        assert len(records) == 5

    def test_get_staff_attendance_empty(self, seeded_db):
        db, staff = seeded_db
        service = StaffAttendanceService(db)
        records = service.get_staff_attendance(staff.id)
        assert records == []

    def test_get_staff_attendance_by_month(self, seeded_db):
        db, staff = seeded_db
        service = StaffAttendanceService(db)
        service.mark_attendance(staff.id, date(2024, 9, 1), AttendanceStatus.present)
        service.mark_attendance(staff.id, date(2024, 10, 1), AttendanceStatus.present)

        records = service.get_staff_attendance(staff.id, month=9, year=2024)
        assert len(records) == 1
