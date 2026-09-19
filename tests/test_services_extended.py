"""Tests for IMS services (smoke tests against the current service API)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestActivityService:
    def test_get_recent_activities(self) -> None:
        from services.activity_service import ActivityService

        db = MagicMock()
        db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        svc = ActivityService(db)
        result = svc.get_logs(limit=10)
        assert isinstance(result, list)

    def test_get_user_logs(self) -> None:
        from services.activity_service import ActivityService

        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        svc = ActivityService(db)
        result = svc.get_user_logs(user_id=1)
        assert isinstance(result, list)


class TestAnalyticsService:
    def test_get_dashboard_kpis(self) -> None:
        from services.analytics_service import AnalyticsService

        db = MagicMock()
        db.query.return_value.count.return_value = 10
        svc = AnalyticsService(db)
        result = svc.get_dashboard_kpis()
        assert isinstance(result, dict)


class TestExportService:
    def test_to_csv_bytes(self) -> None:
        from services.export_service import ExportService

        db = MagicMock()
        db.query.return_value.all.return_value = []
        svc = ExportService(db)
        result = svc.to_csv_bytes([], ["id"])
        assert result.bytes_ == b"\r\ni,d\r\n"
        assert result.mime_type == "text/csv"

    def test_export_unknown_format(self) -> None:
        from services.export_service import ExportError, ExportService

        db = MagicMock()
        svc = ExportService(db)
        with pytest.raises(ExportError):
            svc.export("students.xml", ["id"], [])


class TestNoticeService:
    def test_get_all_notices(self) -> None:
        from services.notice_service import NoticeService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = NoticeService(db)
        result = svc.get_all_notices()
        assert isinstance(result, list)


class TestLeaveService:
    def test_get_all_leaves(self) -> None:
        from services.leave_service import LeaveService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = LeaveService(db)
        result = svc.get_all_leaves()
        assert isinstance(result, list)

    def test_get_leaves_for_user(self) -> None:
        from services.leave_service import LeaveService

        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        svc = LeaveService(db)
        result = svc.get_leaves_for_user(student_id=1)
        assert isinstance(result, list)


class TestFeedbackService:
    def test_get_all_feedback(self) -> None:
        from services.feedback_service import FeedbackService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = FeedbackService(db)
        result = svc.get_all_feedback()
        assert isinstance(result, list)


class TestPlacementService:
    def test_get_all_placements(self) -> None:
        from services.placement_service import PlacementService

        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        svc = PlacementService(db)
        result = svc.get_all_placements()
        assert isinstance(result, list)


class TestResultService:
    def test_get_student_results(self) -> None:
        from services.result_service import ResultService

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        svc = ResultService(db)
        result = svc.get_student_results(student_id=1)
        assert isinstance(result, list)

    def test_get_existing_marks(self) -> None:
        from services.result_service import ResultService

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        svc = ResultService(db)
        result = svc.get_existing_marks(subject_id=1, session_id=1, exam_type="final")
        assert isinstance(result, dict)


class TestStaffService:
    def test_get_all_staff(self) -> None:
        from services.staff_service import StaffService

        db = MagicMock()
        db.query.return_value.count.return_value = 0
        db.query.return_value.all.return_value = []
        svc = StaffService(db)
        result = svc.get_all_staff()
        assert isinstance(result, dict) and "staff" in result

    def test_get_staff_by_id_missing(self) -> None:
        from services.staff_service import StaffService

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        svc = StaffService(db)
        with pytest.raises(ValueError, match="Staff not found"):
            svc.get_staff_by_id(staff_id=999)


class TestStudentService:
    def test_get_all_students(self) -> None:
        from services.student_service import StudentService

        db = MagicMock()
        db.query.return_value.all.return_value = []
        svc = StudentService(db)
        result = svc.get_all_students()
        assert isinstance(result, dict) and "students" in result


class TestCourseService:
    def test_get_all_courses(self) -> None:
        from services.course_service import CourseService

        db = MagicMock()
        db.query.return_value.all.return_value = []
        svc = CourseService(db)
        result = svc.get_all_courses()
        assert isinstance(result, list)
