import os
import sys

import customtkinter as ctk
from tkinter import TclError

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth.session import SessionTracker
from database.db_session import get_db, init_db
from database.seeder import seed_database
from landing.landing_page import LandingPage
from ui.global_search import GlobalSearch
from ui.loading_screen import LoadingScreen
from ui.sidebar import Sidebar
from ui.theme_manager import ThemeManager
from utils.logger import setup_logger

log = setup_logger("bb-ims")


class AppState:
    def __init__(self) -> None:
        self.current_user = None
        self.current_route = None


class BBIMS_App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        # Install global exception handler first so all errors are caught
        self._install_global_exception_handler()

        # Bootstrap: create required directories (uploads, logs, exports)
        from config.settings import init_app

        init_app()

        self.title("Binary Brain Institute Management System")
        self.geometry("1280x720")

        # Center the window
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (1280 / 2)
        y = (screen_height / 2) - (720 / 2)
        self.geometry("%dx%d+%d+%d" % (1280, 720, x, y))

        # Min size
        self.minsize(1024, 768)

        self.tm = ThemeManager(self)
        self.app_state = AppState()
        self.db_session = next(get_db())

        # Global bindings
        self.bind("<Control-k>", lambda e: self.show_global_search())

        # Hide main window during loading
        self.withdraw()

        self.loading = LoadingScreen(self, self.tm)
        self.loading.run_loading(self.on_loading_complete)

    def on_loading_complete(self) -> None:
        init_db()

        # Show landing page immediately, seed in background
        self.deiconify()
        self.show_landing_page()

        # Seed database in a background thread so UI stays responsive
        import threading

        def _seed_task() -> None:
            try:
                seed_database(self.db_session)
            except (OSError, ValueError) as e:
                log.error("Seeding failed: %s", e)

        t = threading.Thread(target=_seed_task, daemon=True)
        t.start()

    def show_landing_page(self) -> None:
        self.clear_main_window()
        self.landing = LandingPage(
            self, self.tm, self.app_state, self.db_session, self.start_main_app
        )
        self.landing.pack(fill="both", expand=True)

    def start_main_app(self) -> None:
        self.clear_main_window()

        # Start Session Tracker
        self.session_tracker = SessionTracker(self.handle_logout, self)
        self.session_tracker.start()

        # Track activity
        self.bind("<Any-KeyPress>", self.session_tracker.update_activity)
        self.bind("<Any-Button>", self.session_tracker.update_activity)
        self.bind("<Motion>", self.session_tracker.update_activity)

        # Layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar
        role = self.app_state.current_user.get("role", "student")
        self.sidebar = Sidebar(self, self.tm, self.navigate, role)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Main Content Area
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # Route to Dashboard
        self.navigate("dashboard")

    def handle_logout(self) -> None:
        if hasattr(self, "session_tracker"):
            self.session_tracker.stop()
        self.app_state.current_user = None
        self.app_state.current_route = None
        self.show_landing_page()

    def clear_main_window(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()

    def show_global_search(self) -> None:
        if self.app_state.current_user:
            GlobalSearch(self, self.navigate)

    def navigate(self, route) -> None:
        if route == "logout":
            self.handle_logout()
            return

        if self.app_state.current_route == route:
            return

        self._prev_route = self.app_state.current_route
        self.app_state.current_route = route

        for widget in self.content_area.winfo_children():
            widget.destroy()

        module_class = self.get_module_class(route)
        if module_class:
            try:
                module_instance = module_class(
                    self.content_area, self.tm, self.app_state, self.db_session
                )
                module_instance.pack(fill="both", expand=True)
            except (OSError, ValueError) as e:
                import traceback as tb_mod

                full_tb = tb_mod.format_exc()
                log.error("Failed to instantiate %s: %s\n%s", route, e, full_tb)
                self.show_error_dialog(f"Failed to open {route}: {e}", full_tb)
                # Stay on current route — restore previous state
                self.app_state.current_route = self._prev_route
        else:
            # _safe_import already showed an error dialog for import failures
            self.app_state.current_route = self._prev_route

    def _safe_import(self, module_path: str, class_name: str) -> None:
        """Safely import a module class, showing an error dialog on failure."""
        import importlib
        import traceback as tb_mod

        try:
            mod = importlib.import_module(module_path)
            return getattr(mod, class_name)
        except (OSError, ValueError) as e:
            full_tb = tb_mod.format_exc()
            log.error("Failed to import %s.%s: %s\n%s", module_path, class_name, e, full_tb)
            self.after(
                0,
                lambda: self.show_error_dialog(
                    f"Failed to load module: {class_name}. The {class_name} feature is unavailable.",
                    full_tb,
                ),
            )
            return None

    def get_module_class(self, route) -> None:
        # Dynamic import based on route and role
        role = self.app_state.current_user.get("role", "student")

        # Shared modules (available to all roles)
        shared_map = {
            "profile": ("modules.shared.profile", "ProfileView"),
            "settings": ("modules.shared.settings_panel", "SettingsPanel"),
            "leave_apply": ("modules.shared.leave_apply", "LeaveApply"),
            "feedback_sender": ("modules.shared.feedback_sender", "FeedbackSender"),
            "notice_viewer": ("modules.shared.notice_viewer", "NoticeViewer"),
        }

        if route in shared_map:
            return self._safe_import(*shared_map[route])

        # Role-specific modules
        role_routes = {
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
                "timetable_scheduler": (
                    "modules.admin.timetable_scheduler",
                    "TimetableScheduler",
                ),
                "analytics_dashboard": (
                    "modules.admin.analytics_dashboard",
                    "AnalyticsDashboard",
                ),
                "staff_attendance": (
                    "modules.admin.staff_attendance_manager",
                    "StaffAttendanceManager",
                ),
                "placement_manager": (
                    "modules.admin.placement_manager",
                    "PlacementManager",
                ),
                "enquiry_manager": ("modules.admin.enquiry_manager", "EnquiryManager"),
                "reports_center": ("modules.admin.reports_center", "ReportsCenter"),
                "activity_logs": (
                    "modules.admin.activity_log_viewer",
                    "ActivityLogViewer",
                ),
            },
            "staff": {
                "dashboard": ("modules.staff.dashboard", "StaffDashboard"),
                "attendance_taker": (
                    "modules.staff.attendance_taker",
                    "AttendanceTaker",
                ),
                "result_manager": ("modules.staff.result_manager", "ResultManager"),
                "student_lookup": ("modules.staff.student_lookup", "StudentLookup"),
                "my_attendance": ("modules.staff.my_attendance", "MyAttendance"),
            },
            "student": {
                "dashboard": ("modules.student.dashboard", "StudentDashboard"),
                "view_attendance": (
                    "modules.student.view_attendance",
                    "ViewAttendance",
                ),
                "view_result": ("modules.student.view_result", "ViewResult"),
                "fee_status": ("modules.student.fee_status", "FeeStatus"),
            },
        }

        mod_entry = role_routes.get(role, {}).get(route)
        if mod_entry:
            return self._safe_import(*mod_entry)

        return None

    def _install_global_exception_handler(self) -> None:
        """Install global exception hooks to show friendly dialogs instead of crashing."""
        import traceback as tb_module

        app = self

        def _handler(exc_type, exc_value, exc_tb) -> None:
            """Catch unhandled exceptions and display a friendly dialog."""
            full_tb = "".join(tb_module.format_exception(exc_type, exc_value, exc_tb))

            # Log to file + console
            log.critical("Unhandled exception:\n%s", full_tb)

            # Show friendly dialog on the main thread
            try:
                app.after(0, lambda: app.show_error_dialog(str(exc_value), full_tb))
            except (TclError, RuntimeError):
                pass  # Give up — nothing else we can do

        # Catch exceptions raised inside Tkinter callbacks (button clicks, bindings)
        self.report_callback_exception = _handler

        # Catch exceptions from other parts of the main thread
        sys.excepthook = _handler

    def show_error_dialog(self, friendly_msg, full_traceback=None) -> None:
        """Show a friendly error dialog with options to restart or exit."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Unexpected Error")
        dialog.geometry("520x320")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.grab_set()
        dialog.focus()

        # Center on parent window
        dialog.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() - 520) // 2
            y = self.winfo_rooty() + (self.winfo_height() - 320) // 2
            dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        except (TclError, RuntimeError):
            pass

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        # Icon
        ctk.CTkLabel(frame, text="⚠️", font=ctk.CTkFont(size=40)).pack(pady=(5, 5))

        # Title
        ctk.CTkLabel(
            frame, text="Something went wrong", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(0, 5))

        # Message
        ctk.CTkLabel(
            frame,
            text=str(friendly_msg),
            text_color="gray",
            wraplength=460,
            justify="center",
        ).pack(pady=(0, 12))

        # Buttons
        accent = getattr(self.tm, "accent_color", "#89b4fa")
        danger = getattr(self.tm, "danger_color", "#f38ba8")

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=5)

        ctk.CTkButton(
            btn_frame,
            text="🔄 Restart",
            command=lambda: self._restart_from_error(dialog),
            fg_color=accent,
            width=120,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame,
            text="✕ Exit",
            command=lambda: self._exit_from_error(dialog),
            fg_color=danger,
            width=120,
        ).pack(side="left", padx=6)

        # Collapsible technical details
        if full_traceback:
            self._add_error_details(frame, full_traceback)

    def _add_error_details(self, parent, traceback_text) -> None:
        """Add a collapsible traceback section to the error dialog."""
        details_frame = ctk.CTkFrame(parent, fg_color="transparent")
        details_frame.pack(fill="x", pady=(8, 0))

        # Create tracebox with full content but start hidden
        tracebox = ctk.CTkTextbox(details_frame, height=80, fg_color=("gray90", "gray10"))
        tracebox.insert("0.0", traceback_text)
        tracebox.configure(state="disabled")

        def toggle() -> None:
            if tracebox.winfo_viewable():
                tracebox.pack_forget()
                toggle_btn.configure(text="📋 Show Details")
            else:
                tracebox.pack(fill="x", pady=5)
                toggle_btn.configure(text="📋 Hide Details")

        toggle_btn = ctk.CTkButton(
            details_frame,
            text="📋 Show Details",
            command=toggle,
            width=130,
            fg_color="gray",
            height=28,
        )
        toggle_btn.pack()

    def _restart_from_error(self, dialog) -> None:
        """Reset app state and return to the landing page."""
        dialog.destroy()
        self._reset_app_state()
        self.clear_main_window()
        self.show_landing_page()

    def _exit_from_error(self, dialog) -> None:
        """Close the dialog and quit the application."""
        dialog.destroy()
        self.quit()

    def _reset_app_state(self) -> None:
        """Safely reset all app state without destroying the window."""
        if hasattr(self, "session_tracker"):
            try:
                self.session_tracker.stop()
            except (OSError, RuntimeError):
                pass
        self.app_state.current_user = None
        self.app_state.current_route = None


if __name__ == "__main__":
    app = BBIMS_App()
    app.mainloop()
