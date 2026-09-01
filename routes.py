"""Route-to-module mapping for the IMS application."""

from __future__ import annotations

from typing import Any

# Shared modules (available to all roles)
SHARED_ROUTES: dict[str, tuple[str, str]] = {
    "profile": ("modules.shared.profile", "ProfileView"),
    "settings": ("modules.shared.settings_panel", "SettingsPanel"),
    "leave_apply": ("modules.shared.leave_apply", "LeaveApply"),
    "feedback_sender": ("modules.shared.feedback_sender", "FeedbackSender"),
    "notice_viewer": ("modules.shared.notice_viewer", "NoticeViewer"),
}

# Role-specific module routes
ROLE_ROUTES: dict[str, dict[str, tuple[str, str]]] = {
    "admin": {
        "dashboard": ("modules.admin.dashboard", "AdminDashboard"),
        "manage_students": ("modules.admin.manage_students", "ManageStudents"),
        "manage_staff": ("modules.admin.manage_staff", "ManageStaff"),
        "manage_courses": ("modules.admin.manage_courses", "ManageCourses"),
        "manage_subjects": ("modules.admin.manage_subjects", "ManageSubjects"),
        "manage_sessions": ("modules.admin.manage_sessions", "ManageSessions"),
        "leave_manager": ("modules.admin.leave_manager", "LeaveManager"),
        "feedback_viewer": ("modules.admin.feedback_viewer", "FeedbackViewer"),
        "fee_management": ("modules.admin.fee_management", "FeeManagement"),
        "notice_board": ("modules.admin.notice_board", "NoticeBoard"),
        "timetable_scheduler": ("modules.admin.timetable_scheduler", "TimetableScheduler"),
        "analytics_dashboard": ("modules.admin.analytics_dashboard", "AnalyticsDashboard"),
        "staff_attendance": ("modules.admin.staff_attendance_manager", "StaffAttendanceManager"),
        "placement_manager": ("modules.admin.placement_manager", "PlacementManager"),
        "enquiry_manager": ("modules.admin.enquiry_manager", "EnquiryManager"),
        "reports_center": ("modules.admin.reports_center", "ReportsCenter"),
        "activity_logs": ("modules.admin.activity_log_viewer", "ActivityLogViewer"),
    },
    "staff": {
        "dashboard": ("modules.staff.dashboard", "StaffDashboard"),
        "attendance_taker": ("modules.staff.attendance_taker", "AttendanceTaker"),
        "result_manager": ("modules.staff.result_manager", "ResultManager"),
        "student_lookup": ("modules.staff.student_lookup", "StudentLookup"),
        "my_attendance": ("modules.staff.my_attendance", "MyAttendance"),
    },
    "student": {
        "dashboard": ("modules.student.dashboard", "StudentDashboard"),
        "view_attendance": ("modules.student.view_attendance", "ViewAttendance"),
        "view_result": ("modules.student.view_result", "ViewResult"),
        "fee_status": ("modules.student.fee_status", "FeeStatus"),
    },
}


def resolve_route(route: str, role: str) -> tuple[str, str] | None:
    """Resolve a route name to a (module_path, class_name) tuple."""
    if route in SHARED_ROUTES:
        return SHARED_ROUTES[route]
    return ROLE_ROUTES.get(role, {}).get(route)
