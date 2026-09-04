"""
Comprehensive test script to verify:
1. Database initialization & seeding works
2. Admin login with demo credentials
3. All module classes can be imported (navigation viability)
"""

import os
import traceback

import pytest
import structlog

logger = structlog.get_logger("test_ui_flow")

pytestmark = pytest.mark.unit
pytestmark = pytest.mark.slow

import pytest

if __name__ != "__main__":
    # This is a standalone script (not a proper pytest test file).
    # It should NOT execute during pytest collection — the top-level
    # code would run and may interfere with the database.
    # Pytest will skip this file entirely.
    pytest.skip("Standalone script — not a pytest test", allow_module_level=True)

# --- Step 1: Init DB ---
logger.info("step_1_database_init")

from database.db_session import SessionLocal, init_db
from database.models import User
from database.seeder import seed_database

# Remove existing DB first for a clean start
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bbims.db")
if os.path.exists(db_path):
    os.remove(db_path)
    logger.info("db_removed", path=db_path)

init_db()
logger.info("database_tables_created")

db = SessionLocal()
try:
    seed_database(db)
    logger.info("database_seeded")

    # Verify admin user exists
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        logger.info("admin_user_found", id=admin.id, role=admin.role.value)
    else:
        logger.error("admin_user_not_found")
        sys.exit(1)
finally:
    db.close()

# --- Step 2: Test Login ---
logger.info("step_2_admin_login")

from services.auth_service import AuthError, AuthService

db = SessionLocal()
try:
    auth_service = AuthService(db)

    # Get admin password from environment or seeder module
    admin_pwd = os.environ.get("DEMO_ADMIN_PASSWORD")
    if not admin_pwd:
        try:
            from database.seeder import DEMO_ADMIN_PASSWORD


            admin_pwd = DEMO_ADMIN_PASSWORD
        except (ImportError, AttributeError):
            admin_pwd = None

    if not admin_pwd:
        logger.info("admin_password_not_set")
    else:
        try:
            result = auth_service.login("admin", admin_pwd)
            logger.info("admin_login_succeeded", role=result['role'], user_id=result['user_id'])

            # Verify OTP
            otp_result = auth_service.verify_otp(
                result["user_id"], result["otp_code"], result["otp_code"]
            )
            logger.info("otp_verification_succeeded", user=otp_result['user']['name'])
        except AuthError as e:
            logger.warning("admin_login_failed", error=str(e))
            # Try alternative password from environment
            fallback_pwd = os.environ.get("DEMO_ADMIN_FALLBACK_PASSWORD")
            if fallback_pwd:
                try:
                    result = auth_service.login("admin", fallback_pwd)
                    logger.info("admin_login_fallback_succeeded", role=result['role'])
                    otp_result = auth_service.verify_otp(
                        result["user_id"], result["otp_code"], result["otp_code"]
                    )
                    logger.info("otp_verification_succeeded", user=otp_result['user']['name'])
                except AuthError as e2:
                    logger.error("admin_login_fallback_failed", error=str(e2))
except (OSError, ValueError, KeyError) as e:
    logger.error("login_test_error", error=str(e), traceback=traceback.format_exc())
finally:
    db.close()

# --- Step 3: Test All Module Imports ---
logger.info("step_3_module_imports")


# Mock a ThemeManager-like class and AppState for instantiation tests
class MockTM:
    bg_color = "#1e1e2e"
    accent_color = "#89b4fa"
    success_color = "#a6e3a1"
    danger_color = "#f38ba8"
    header_font = ("Arial", 20, "bold")
    main_font = ("Arial", 14)
    small_font = ("Arial", 10)


imports_failed = []

# Map of all routes to (module_path, class_name, role)
module_routes = {
    # Shared
    "profile": ("modules.shared.profile", "ProfileView"),
    "settings": ("modules.shared.settings_panel", "SettingsPanel"),
    "leave_apply": ("modules.shared.leave_apply", "LeaveApply"),
    "feedback_sender": ("modules.shared.feedback_sender", "FeedbackSender"),
    "notice_viewer": ("modules.shared.notice_viewer", "NoticeViewer"),
    # Admin
    "dashboard_admin": ("modules.admin.dashboard", "AdminDashboard"),
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
    "staff_attendance": (
        "modules.admin.staff_attendance_manager",
        "StaffAttendanceManager",
    ),
    "placement_manager": ("modules.admin.placement_manager", "PlacementManager"),
    "enquiry_manager": ("modules.admin.enquiry_manager", "EnquiryManager"),
    "reports_center": ("modules.admin.reports_center", "ReportsCenter"),
    "activity_logs": ("modules.admin.activity_log_viewer", "ActivityLogViewer"),
    # Staff
    "dashboard_staff": ("modules.staff.dashboard", "StaffDashboard"),
    "attendance_taker": ("modules.staff.attendance_taker", "AttendanceTaker"),
    "result_manager": ("modules.staff.result_manager", "ResultManager"),
    "student_lookup": ("modules.staff.student_lookup", "StudentLookup"),
    "my_attendance": ("modules.staff.my_attendance", "MyAttendance"),
    # Student
    "dashboard_student": ("modules.student.dashboard", "StudentDashboard"),
    "view_attendance": ("modules.student.view_attendance", "ViewAttendance"),
    "view_result": ("modules.student.view_result", "ViewResult"),
    "fee_status": ("modules.student.fee_status", "FeeStatus"),
}

for route, (mod_path, cls_name) in module_routes.items():
    try:
        importlib = __import__(mod_path, fromlist=[cls_name])
        cls = getattr(importlib, cls_name)
        logger.info("module_import_ok", route=route, module=f"{mod_path}.{cls_name}")
    except (ImportError, AttributeError, OSError) as e:
        imports_failed.append((route, mod_path, cls_name, str(e)))
        logger.warning("module_import_failed", route=route, error=str(e))

if imports_failed:
    logger.warning("modules_failed", count=len(imports_failed))
else:
    logger.info("all_modules_imported", count=len(module_routes))

# --- Step 4: Test Shared Service Imports ---
logger.info("step_4_service_imports")

service_imports: list[tuple[str, str | None]] = [
    ("services.activity_service", "ActivityService"),
    ("services.analytics_service", "AnalyticsService"),
    ("services.attendance_service", "AttendanceService"),
    ("services.course_service", "CourseService"),
    ("services.export_service", "ExportService"),
    ("services.feedback_service", "FeedbackService"),
    ("services.fee_service", "FeeService"),
    ("services.leave_service", "LeaveService"),
    ("services.notice_service", "NoticeService"),
    ("services.placement_service", "PlacementService"),
    ("services.result_service", "ResultService"),
    ("services.search_service", "SearchService"),
    ("services.staff_attendance_service", "StaffAttendanceService"),
    ("services.staff_service", "StaffService"),
    ("services.student_service", "StudentService"),
    ("ui.chart_factory", "ChartFactory"),
    ("ui.global_search", "GlobalSearch"),
    ("ui.toast", "ToastManager"),
    ("ui.animations", "CounterAnimation"),
    ("ui.data_table", "DataTable"),
    ("ui.components", None),
    ("ui.sidebar", "Sidebar"),
    ("utils.helpers", None),
    ("utils.validators", None),
    ("utils.async_loader", None),
]

svc_failed = []
for mod_path, cls_name in service_imports:
    try:
        mod = __import__(mod_path, fromlist=[cls_name] if cls_name else [])
        if cls_name:
            getattr(mod, cls_name)
        logger.info("service_import_ok", module=mod_path + (f".{cls_name}" if cls_name else ""))
    except (ImportError, AttributeError, OSError) as e:
        svc_failed.append((mod_path, str(e)))
        logger.warning("service_import_failed", module=mod_path, error=str(e))

if svc_failed:
    logger.warning("services_failed", count=len(svc_failed))

# --- Summary ---
if not imports_failed and not svc_failed:
    logger.info("all_imports_successful")
else:
    if imports_failed:
        logger.warning("module_imports_failed", count=len(imports_failed))
    if svc_failed:
        logger.warning("service_imports_failed", count=len(svc_failed))

logger.info("audit_complete", total_modules=len(module_routes), total_services=len(service_imports))
