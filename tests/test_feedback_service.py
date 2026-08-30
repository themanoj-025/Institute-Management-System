"""Tests for FeedbackService."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import User, UserRole
from services.feedback_service import FeedbackService


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
def test_user(db_session):
    user = User(
        username="feedback_user",
        password_hash="hash",
        role=UserRole.student,
        email="fb@bb.edu.in",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session):
    user = User(
        username="admin_fb",
        password_hash="hash",
        role=UserRole.admin,
        email="admin@bb.edu.in",
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestFeedbackService:
    def test_submit_feedback(self, db_session, test_user) -> None:
        service = FeedbackService(db_session)
        result = service.submit_feedback(test_user.id, "General", "Great institute!")
        assert result["category"] == "General"
        assert result["message"] == "Great institute!"

    def test_submit_feedback_with_reply(self, db_session, test_user, admin_user) -> None:
        service = FeedbackService(db_session)
        fb = service.submit_feedback(test_user.id, "Academic", "Need more labs")
        assert fb["reply"] is None

        # Reply to feedback
        replied = service.reply_to_feedback(fb["id"], admin_user.id, "Labs are coming soon!")
        assert replied["reply"] == "Labs are coming soon!"
        assert replied["replied_on"] is not None

    def test_get_user_feedback(self, db_session, test_user) -> None:
        service = FeedbackService(db_session)
        for i in range(3):
            service.submit_feedback(test_user.id, f"Category {i}", f"Message {i}")

        feedbacks = service.get_user_feedback(test_user.id)
        assert len(feedbacks) == 3
        assert feedbacks[0]["category"] == "Category 2"  # desc order

    def test_get_user_feedback_empty(self, db_session) -> None:
        service = FeedbackService(db_session)
        feedbacks = service.get_user_feedback(999)
        assert feedbacks == []

    def test_get_all_feedback(self, db_session, test_user) -> None:
        service = FeedbackService(db_session)
        service.submit_feedback(test_user.id, "General", "Message 1")

        all_fb = service.get_all_feedback()
        assert len(all_fb) == 1

    def test_reply_to_nonexistent_feedback(self, db_session, admin_user) -> None:
        service = FeedbackService(db_session)
        result = service.reply_to_feedback(999, admin_user.id, "Reply")
        assert result is None

    def test_feedback_format(self, db_session, test_user) -> None:
        service = FeedbackService(db_session)
        result = service.submit_feedback(test_user.id, "Test", "Hello")
        assert "id" in result
        assert "submitted_on" in result
        assert "user" in result
        assert result["user"] == "feedback_user"
