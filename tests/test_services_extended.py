"""Tests for IMS services."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestActivityService:
    def test_get_recent_activities(self) -> None:
        from services.activity_service import ActivityService

        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        svc = ActivityService(db)
        result = svc.get_recent_activities()
        assert isinstance(result, list)


class TestAnalyticsService:
    def test_get_dashboard_stats(self) -> None:
        from services.analytics_service import AnalyticsService

        db = MagicMock()
        db.query.return_value.count.return_value = 10
        svc = AnalyticsService(db)
        result = svc.get_dashboard_stats()
        assert isinstance(result, dict)


class TestExportService:
    def test_export_students_csv(self) -> None:
        from services.export_service import ExportService

        db = MagicMock()
        db.query.return_value.all.return_value = []
        svc = ExportService(db)
        result = svc.export_students_csv()
        assert isinstance(result, (str, bytes, type(None)))


class TestNoticeService:
    def test_get_notices(self) -> None:
        from services.notice_service import NoticeService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = NoticeService(db)
        result = svc.get_notices()
        assert isinstance(result, list)


class TestLeaveService:
    def test_get_leave_requests(self) -> None:
        from services.leave_service import LeaveService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = LeaveService(db)
        result = svc.get_leave_requests()
        assert isinstance(result, list)


class TestFeedbackService:
    def test_get_feedback(self) -> None:
        from services.feedback_service import FeedbackService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = FeedbackService(db)
        result = svc.get_feedback()
        assert isinstance(result, list)


class TestPlacementService:
    def test_get_placements(self) -> None:
        from services.placement_service import PlacementService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = PlacementService(db)
        result = svc.get_placements()
        assert isinstance(result, list)


class TestResultService:
    def test_get_results(self) -> None:
        from services.result_service import ResultService

        db = MagicMock()
        db.query.return_value.all.return_value = []
        svc = ResultService(db)
        result = svc.get_results()
        assert isinstance(result, list)


class TestStaffService:
    def test_get_staff(self) -> None:
        from services.staff_service import StaffService

        db = MagicMock()
        db.query.return_value.all.return_value = []
        svc = StaffService(db)
        result = svc.get_staff()
        assert isinstance(result, list)


class TestStudentService:
    def test_get_students(self) -> None:
        from services.student_service import StudentService

        db = MagicMock()
        db.query.return_value.all.return_value = []
        svc = StudentService(db)
        result = svc.get_students()
        assert isinstance(result, list)


class TestCourseService:
    def test_get_courses(self) -> None:
        from services.course_service import CourseService

        db = MagicMock()
        db.query.return_value.all.return_value = []
        svc = CourseService(db)
        result = svc.get_courses()
        assert isinstance(result, list)
