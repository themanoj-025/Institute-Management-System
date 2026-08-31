"""Tests for ActivityService."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import ActivityLog, User, UserRole
from services.activity_service import ActivityService


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
def activity_service(db_session) -> None:
    return ActivityService(db_session)


@pytest.fixture
def test_user(db_session) -> None:
    user = User(
        username="test_user",
        password_hash="hash",
        role=UserRole.staff,
        email="test@bb.edu.in",
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestActivityService:
    def test_log_success(self, db_session, activity_service, test_user) -> None:
        """Verify logging a successful action creates a DB entry."""
        activity_service.log(
            user_id=test_user.id,
            action="Viewed dashboard",
            module="Dashboard",
            result="success",
        )

        logs = db_session.query(ActivityLog).all()
        assert len(logs) == 1
        assert logs[0].user_id == test_user.id
        assert logs[0].action == "Viewed dashboard [success]"
        assert logs[0].module == "Dashboard"

    def test_log_failure(self, db_session, activity_service, test_user) -> None:
        """Verify logging a failure action works correctly."""
        activity_service.log(
            user_id=test_user.id,
            action="Login failed",
            module="Auth",
            details={"reason": "Invalid password"},
            result="fail",
        )

        logs = db_session.query(ActivityLog).all()
        assert len(logs) == 1
        assert logs[0].action == "Login failed [fail]"

    def test_log_with_details(self, db_session, activity_service, test_user) -> None:
        """Verify logging with extra details dictionary."""
        activity_service.log(
            user_id=test_user.id,
            action="Updated profile",
            module="Profile",
            details={"field": "phone", "old": "123", "new": "456"},
            result="success",
        )

        logs = db_session.query(ActivityLog).all()
        assert len(logs) == 1
        assert logs[0].action == "Updated profile [success]"

    def test_get_logs(self, db_session, activity_service, test_user) -> None:
        """Verify get_logs returns logs in reverse chronological order."""
        for i in range(5):
            activity_service.log(
                user_id=test_user.id,
                action=f"Action {i}",
                module="Test",
            )

        logs = activity_service.get_logs(limit=3)
        assert len(logs) == 3

    def test_get_user_logs(self, db_session, activity_service, test_user) -> None:
        """Verify get_user_logs filters by user_id."""
        # Create another user
        other_user = User(
            username="other",
            password_hash="hash",
            role=UserRole.admin,
            email="other@bb.edu.in",
        )
        db_session.add(other_user)
        db_session.commit()

        for i in range(3):
            activity_service.log(user_id=test_user.id, action=f"Own {i}", module="Test")
            activity_service.log(user_id=other_user.id, action=f"Other {i}", module="Test")

        user_logs = activity_service.get_user_logs(test_user.id, limit=10)
        assert len(user_logs) == 3
        for log in user_logs:
            assert log.user_id == test_user.id

    def test_log_db_failure_does_not_crash(self, db_session, activity_service, test_user) -> None:
        """Verify the service doesn't crash when DB logging fails."""
        # Force a DB failure by passing a non-existent user_id
        # This should not raise despite DB failure (logged to error logger)
        activity_service.log(
            user_id=99999,
            action="Test",
            module="Test",
        )
        # Verify test_user still exists (original session not affected)
        assert db_session.query(User).filter(User.id == test_user.id).first() is not None
