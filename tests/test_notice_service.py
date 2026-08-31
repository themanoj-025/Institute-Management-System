"""Tests for NoticeService."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from database.models import User, UserRole
from services.notice_service import NoticeService


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
def admin_user(db_session) -> None:
    user = User(
        username="admin_note",
        password_hash="hash",
        role=UserRole.admin,
        email="admin@bb.edu.in",
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestNoticeService:
    def test_create_notice(self, db_session, admin_user) -> None:
        service = NoticeService(db_session)
        result = service.create_notice(
            title="Holiday Notice",
            content="Institute closed on Friday",
            author_id=admin_user.id,
            target_role="all",
        )
        assert result["title"] == "Holiday Notice"
        assert result["content"] == "Institute closed on Friday"
        assert result["is_pinned"] is False

    def test_create_pinned_notice(self, db_session, admin_user) -> None:
        service = NoticeService(db_session)
        result = service.create_notice(
            title="Important",
            content="Exam schedule",
            author_id=admin_user.id,
            target_role="student",
            is_pinned=True,
        )
        assert result["is_pinned"] is True

    def test_get_all_notices(self, db_session, admin_user) -> None:
        service = NoticeService(db_session)
        for i in range(3):
            service.create_notice(
                title=f"Notice {i}", content=f"Content {i}", author_id=admin_user.id
            )

        notices = service.get_all_notices()
        assert len(notices) == 3

    def test_get_notices_by_target_role(self, db_session, admin_user) -> None:
        service = NoticeService(db_session)
        service.create_notice(
            title="All", content="All", author_id=admin_user.id, target_role="all"
        )
        service.create_notice(
            title="Students",
            content="Students",
            author_id=admin_user.id,
            target_role="student",
        )
        service.create_notice(
            title="Staff", content="Staff", author_id=admin_user.id, target_role="staff"
        )

        # "all" role should see notices for "all" and their role
        student_notices = service.get_all_notices(target_role="student")
        assert len(student_notices) == 2  # "all" + "students"

    def test_delete_notice(self, db_session, admin_user) -> None:
        service = NoticeService(db_session)
        result = service.create_notice(title="Delete Me", content="Gone", author_id=admin_user.id)
        notice_id = result["id"]

        assert service.delete_notice(notice_id) is True
        remaining = service.get_all_notices()
        assert len(remaining) == 0

    def test_pinned_notices_first(self, db_session, admin_user) -> None:
        service = NoticeService(db_session)
        service.create_notice(
            title="Regular", content="Regular", author_id=admin_user.id, is_pinned=False
        )
        service.create_notice(
            title="Pinned", content="Important", author_id=admin_user.id, is_pinned=True
        )

        notices = service.get_all_notices()
        assert notices[0]["is_pinned"] is True
        assert notices[0]["title"] == "Pinned"

    def test_notice_format(self, db_session, admin_user) -> None:
        service = NoticeService(db_session)
        result = service.create_notice(title="Test", content="Test", author_id=admin_user.id)
        assert "id" in result
        assert "author" in result
        assert "date" in result
        assert "target_role" in result
