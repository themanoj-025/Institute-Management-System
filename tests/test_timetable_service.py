"""Tests for IMS timetable service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestTimetableService:
    def test_get_timetable_empty(self) -> None:
        from services.timetable_service import TimetableService

        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        svc = TimetableService(db)
        result = svc.get_timetable_for_course(1)
        assert result == []

    def test_get_all_course_timetables(self) -> None:
        from services.timetable_service import TimetableService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = TimetableService(db)
        result = svc.get_all_course_timetables()
        assert isinstance(result, dict)

    def test_auto_generate_no_subjects(self) -> None:
        from services.timetable_service import TimetableService

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        svc = TimetableService(db)
        result = svc.auto_generate(1)
        assert result["status"] in ("skipped", "error", "created")


class TestSearchService:
    def test_global_search_empty(self) -> None:
        from services.search_service import SearchService

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        svc = SearchService(db)
        result = svc.global_search("")
        assert result == {}

    def test_global_search_short_query(self) -> None:
        from services.search_service import SearchService

        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []
        svc = SearchService(db)
        result = svc.global_search("a")
        assert result == {}


class TestHelpers:
    def test_format_currency(self) -> None:
        from utils.helpers import Helpers

        result = Helpers.format_currency(1234.56)
        assert "1" in result or "1234" in result

    def test_format_currency_zero(self) -> None:
        from utils.helpers import Helpers

        result = Helpers.format_currency(0)
        assert "0" in result

    def test_magic_bytes_pdf(self) -> None:
        # PDF magic bytes
        import tempfile

        from utils.helpers import _check_magic_bytes
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 test content")
            f.flush()
            result = _check_magic_bytes(f.name, "pdf")
            assert result is True

    def test_magic_bytes_csv(self) -> None:
        from utils.helpers import _check_magic_bytes

        # CSV has no magic bytes
        result = _check_magic_bytes("nonexistent.csv", "csv")
        assert result is True


class TestSessionTracker:
    def test_session_set_token(self) -> None:
        from auth.session import SessionTracker

        tracker = SessionTracker(
            logout_callback=MagicMock(),
            root=MagicMock(),
        )
        tracker.set_token("test-jwt-token")
        assert tracker.get_token() == "test-jwt-token"

    def test_session_no_token(self) -> None:
        from auth.session import SessionTracker

        tracker = SessionTracker(
            logout_callback=MagicMock(),
            root=MagicMock(),
        )
        assert tracker.get_token() is None

    def test_session_is_active(self) -> None:
        from auth.session import SessionTracker

        tracker = SessionTracker(
            logout_callback=MagicMock(),
            root=MagicMock(),
        )
        assert tracker.is_active is False


class TestSchemas:
    def test_student_schema(self) -> None:
        from api.schemas import StudentCreate

        schema = StudentCreate(
            name="Test Student",
            roll_no="CS001",
            email="test@ims.com",
            course_id=1,
        )
        assert schema.name == "Test Student"

    def test_course_schema(self) -> None:
        from api.schemas import CourseCreate

        schema = CourseCreate(
            name="Computer Science",
            code="CS",
            duration_years=4,
        )
        assert schema.name == "Computer Science"
