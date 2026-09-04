"""
Unit tests for error handling in main.py:
- navigate() error recovery via _prev_route
- _safe_import() catches failures gracefully
- get_module_class() routing
- show_error_dialog() and related helpers
- _install_global_exception_handler()
- _reset_app_state()
"""

import os
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------- AppState ----------


class TestAppState:
    """AppState is a simple data class used to track app state."""

    def test_default_initialization(self) -> None:
        from main import AppState

        state = AppState()
        assert state.current_user is None
        assert state.current_route is None

    def test_set_values(self) -> None:
        from main import AppState

        state = AppState()
        state.current_user = {"id": 1, "role": "admin"}
        state.current_route = "dashboard"
        assert state.current_user["role"] == "admin"
        assert state.current_route == "dashboard"


# ---------- Mock helpers ----------


@pytest.fixture
def mock_ctk_app() -> None:
    """Create a mock BBIMS_App instance with all GUI dependencies patched."""
    # Save sys.excepthook so _install_global_exception_handler tests don't leak
    original_excepthook = sys.excepthook

    with patch.multiple(
        "main",
        ctk=MagicMock(),
        ThemeManager=MagicMock(),
        LoadingScreen=MagicMock(),
        LandingPage=MagicMock(),
        Sidebar=MagicMock(),
        GlobalSearch=MagicMock(),
        SessionTracker=MagicMock(),
        get_db=MagicMock(return_value=iter([MagicMock()])),
        init_db=MagicMock(),
        seed_database=MagicMock(),
    ):
        from main import AppState, BBIMS_App

        app = BBIMS_App.__new__(BBIMS_App)
        # Manually set up the minimal attributes needed for tests
        app.tm = MagicMock()
        app.tm.accent_color = "#89b4fa"
        app.tm.danger_color = "#f38ba8"
        app.app_state = AppState()
        app.app_state.current_user = {"id": 1, "role": "admin", "username": "admin"}
        app.db_session = MagicMock()
        app.content_area = MagicMock()
        app.content_area.winfo_children = MagicMock(return_value=[])
        # Mock the important dialog/tk methods
        app.winfo_screenwidth = MagicMock(return_value=1920)
        app.winfo_screenheight = MagicMock(return_value=1080)
        app.winfo_rootx = MagicMock(return_value=0)
        app.winfo_rooty = MagicMock(return_value=0)
        app.winfo_width = MagicMock(return_value=1280)
        app.winfo_height = MagicMock(return_value=720)
        app.after = MagicMock()
        app.quit = MagicMock()
        app.withdraw = MagicMock()
        app.deiconify = MagicMock()
        app.bind = MagicMock()
        app.grid_rowconfigure = MagicMock()
        app.grid_columnconfigure = MagicMock()
        app.title = MagicMock()
        app.geometry = MagicMock()
        app.minsize = MagicMock()
        # Override show_error_dialog to avoid creating real windows
        app.show_error_dialog = MagicMock()
        app._add_error_details = MagicMock()
        app._show_error_dialog_called = False
        app._last_error_msg = None
        app._last_error_tb = None
        app.tk = MagicMock()
        yield app

    # Restore sys.excepthook to avoid leaking to other tests
    sys.excepthook = original_excepthook


# ---------- _safe_import ----------


class TestSafeImport:
    """_safe_import should safely import modules and fail gracefully."""

    def test_import_valid_module(self, mock_ctk_app) -> None:
        """Importing a known-good module should return its class."""
        cls = mock_ctk_app._safe_import("services.auth_service", "AuthService")
        from services.auth_service import AuthService

        assert cls is AuthService
        mock_ctk_app.after.assert_not_called()  # No error dialog

    def test_import_nonexistent_module(self, mock_ctk_app) -> None:
        """Importing a non-existent module should return None and show error dialog."""
        cls = mock_ctk_app._safe_import("modules.nonexistent", "FakeClass")
        assert cls is None
        # Should have scheduled an error dialog via after()
        mock_ctk_app.after.assert_called_once()
        args, _ = mock_ctk_app.after.call_args
        assert args[0] == 0  # Delay is 0

    def test_import_nonexistent_class(self, mock_ctk_app) -> None:
        """Importing a non-existent class from an existing module should return None."""
        cls = mock_ctk_app._safe_import("services.auth_service", "NonExistentClass")
        assert cls is None
        mock_ctk_app.after.assert_called_once()

    def test_import_with_invalid_module_path(self, mock_ctk_app) -> None:
        """Importing with a completely invalid path should return None."""
        cls = mock_ctk_app._safe_import("", "")
        assert cls is None
        mock_ctk_app.after.assert_called_once()


# ---------- get_module_class ----------


class TestGetModuleClass:
    """get_module_class should route correctly based on role."""

    def test_shared_route(self, mock_ctk_app) -> None:
        """Shared routes should be resolvable for any role."""
        from modules.shared.profile import ProfileView

        result = mock_ctk_app.get_module_class("profile")
        assert result is ProfileView

    def test_admin_route(self, mock_ctk_app) -> None:
        """Admin-specific routes should work when role is admin."""
        from modules.admin.dashboard import AdminDashboard

        result = mock_ctk_app.get_module_class("dashboard")
        assert result is AdminDashboard

    def test_student_route_with_admin_role(self, mock_ctk_app) -> None:
        """Staff routes should fail when role is admin (returns None via _safe_import)."""
        mock_ctk_app.app_state.current_user = {"id": 1, "role": "admin"}
        result = mock_ctk_app.get_module_class("my_attendance")  # Staff route
        # _safe_import will fail because it's not in admin's route map
        assert result is None

    def test_nonexistent_route(self, mock_ctk_app) -> None:
        """A completely unknown route should return None."""
        result = mock_ctk_app.get_module_class("this_route_does_not_exist")
        assert result is None

    def test_staff_route(self, mock_ctk_app) -> None:
        """Staff-specific routes should work when role is staff."""
        mock_ctk_app.app_state.current_user = {"id": 2, "role": "staff"}
        from modules.staff.dashboard import StaffDashboard

        result = mock_ctk_app.get_module_class("dashboard")
        assert result is StaffDashboard

    def test_student_route(self, mock_ctk_app) -> None:
        """Student-specific routes should work when role is student."""
        mock_ctk_app.app_state.current_user = {"id": 3, "role": "student"}
        from modules.student.dashboard import StudentDashboard

        result = mock_ctk_app.get_module_class("dashboard")
        assert result is StudentDashboard

    def test_admin_only_routes(self, mock_ctk_app) -> None:
        """Admin-only routes like manage_students should not work for students."""
        mock_ctk_app.app_state.current_user = {"id": 3, "role": "student"}
        result = mock_ctk_app.get_module_class("manage_students")
        assert result is None


# ---------- navigate ----------


class TestNavigate:
    """navigate() should handle errors gracefully with _prev_route recovery."""

    def test_navigate_logout(self, mock_ctk_app) -> None:
        """Navigating to 'logout' should call handle_logout."""
        mock_ctk_app.handle_logout = MagicMock()
        mock_ctk_app.navigate("logout")
        mock_ctk_app.handle_logout.assert_called_once()

    def test_navigate_same_route(self, mock_ctk_app) -> None:
        """Navigating to the current route should be a no-op."""
        mock_ctk_app.app_state.current_route = "dashboard"
        mock_ctk_app.get_module_class = MagicMock()  # Should NOT be called
        mock_ctk_app.navigate("dashboard")
        mock_ctk_app.get_module_class.assert_not_called()

    def test_navigate_unknown_route_restores_prev_route(self, mock_ctk_app) -> None:
        """Navigating to an unknown route should restore _prev_route."""
        mock_ctk_app.app_state.current_route = "dashboard"
        mock_ctk_app.navigate("non_existent_route")
        # Should restore to the previous route
        assert mock_ctk_app.app_state.current_route == "dashboard"

    def test_navigate_sets_prev_route(self, mock_ctk_app) -> None:
        """navigate() should save _prev_route before changing current_route."""

        class DummyModule:
            def __init__(self, *args, **kwargs):
                pass

            def pack(self, *args, **kwargs) -> None:
                pass

        mock_ctk_app.app_state.current_route = "settings"
        mock_ctk_app.get_module_class = MagicMock(return_value=DummyModule)
        mock_ctk_app.navigate("dashboard")
        assert mock_ctk_app._prev_route == "settings"
        assert mock_ctk_app.app_state.current_route == "dashboard"

    def test_navigate_module_import_failure(self, mock_ctk_app) -> None:
        """If get_module_class fails, navigate should restore _prev_route."""
        mock_ctk_app.app_state.current_route = "settings"

        # get_module_class returns a class that raises on construction
        class FailingModule:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("Module init failed!")

        # Make sure _safe_import returns None for the failing path
        # by monkeypatching get_module_class
        mock_ctk_app.get_module_class = MagicMock(return_value=FailingModule)
        mock_ctk_app.navigate("some_route")
        # Should restore to previous route
        assert mock_ctk_app.app_state.current_route == "settings"

    def test_navigate_clears_content_area(self, mock_ctk_app) -> None:
        """navigate() should destroy existing widgets in content_area."""
        children = [MagicMock() for _ in range(3)]
        mock_ctk_app.content_area.winfo_children = MagicMock(return_value=children)
        mock_ctk_app.get_module_class = MagicMock(return_value=None)
        mock_ctk_app.app_state.current_route = "settings"
        mock_ctk_app.navigate("non_existent")
        for child in children:
            child.destroy.assert_called_once()

    def test_navigate_success_path(self, mock_ctk_app) -> None:
        """Successful navigation should leave current_route unchanged."""

        class DummyModule:
            def __init__(self, *args, **kwargs):
                pass

            def pack(self, *args, **kwargs) -> None:
                pass

        mock_ctk_app.app_state.current_route = "settings"
        mock_ctk_app.get_module_class = MagicMock(return_value=DummyModule)
        mock_ctk_app.navigate("profile")
        assert mock_ctk_app.app_state.current_route == "profile"


# ---------- show_error_dialog ----------


class TestErrorDialog:
    """Test show_error_dialog with real method but mocked widgets."""

    def test_creates_dialog_with_correct_title(self, mock_ctk_app) -> None:
        """Dialog should have the correct title and attributes."""
        with patch("main.ctk.CTkToplevel") as mock_toplevel_cls:
            mock_dialog = MagicMock()
            mock_toplevel_cls.return_value = mock_dialog

            # We need to temporarily replace show_error_dialog with the real one
            import main as main_module

            mock_ctk_app.show_error_dialog
            mock_ctk_app.show_error_dialog = main_module.BBIMS_App.show_error_dialog.__get__(
                mock_ctk_app, main_module.BBIMS_App
            )

            mock_ctk_app.show_error_dialog("Test error message")

            mock_dialog.title.assert_called_with("Unexpected Error")
            mock_dialog.attributes.assert_called_with("-topmost", True)
            mock_dialog.grab_set.assert_called_once()
            mock_dialog.focus.assert_called_once()
            mock_dialog.resizable.assert_called_with(False, False)

    def test_dialog_with_traceback_calls_add_details(self, mock_ctk_app) -> None:
        """When full_traceback is provided, _add_error_details should be called."""
        with patch("main.ctk.CTkToplevel") as mock_toplevel_cls:
            mock_dialog = MagicMock()
            mock_toplevel_cls.return_value = mock_dialog

            import main as main_module

            mock_ctk_app.show_error_dialog = main_module.BBIMS_App.show_error_dialog.__get__(
                mock_ctk_app, main_module.BBIMS_App
            )
            mock_ctk_app._add_error_details = MagicMock()

            mock_ctk_app.show_error_dialog("Error", "Traceback line 1\nTraceback line 2")

            mock_ctk_app._add_error_details.assert_called_once()

    def test_dialog_without_traceback_skips_details(self, mock_ctk_app) -> None:
        """When full_traceback is None, _add_error_details should NOT be called."""
        with patch("main.ctk.CTkToplevel") as mock_toplevel_cls:
            mock_dialog = MagicMock()
            mock_toplevel_cls.return_value = mock_dialog

            import main as main_module

            mock_ctk_app.show_error_dialog = main_module.BBIMS_App.show_error_dialog.__get__(
                mock_ctk_app, main_module.BBIMS_App
            )
            mock_ctk_app._add_error_details = MagicMock()

            mock_ctk_app.show_error_dialog("Error")

            mock_ctk_app._add_error_details.assert_not_called()


# ---------- _add_error_details ----------


class TestAddErrorDetails:
    """_add_error_details should create a collapsible traceback section."""

    def test_creates_toggle_button(self, mock_ctk_app) -> None:
        """_add_error_details should create a toggle button and a textbox."""
        with patch("main.ctk.CTkFrame") as mock_frame_cls:
            mock_frame = MagicMock()
            mock_frame_cls.return_value = mock_frame

            with patch("main.ctk.CTkTextbox") as mock_textbox_cls:
                mock_textbox = MagicMock()
                mock_textbox_cls.return_value = mock_textbox
                mock_textbox.winfo_viewable = MagicMock(return_value=False)

                with patch("main.ctk.CTkButton") as mock_btn_cls:
                    mock_btn = MagicMock()
                    mock_btn_cls.return_value = mock_btn

                    import main as main_module

                    mock_ctk_app._add_error_details = (
                        main_module.BBIMS_App._add_error_details.__get__(
                            mock_ctk_app, main_module.BBIMS_App
                        )
                    )
                    mock_ctk_app._add_error_details(MagicMock(), "test traceback")

                    # Textbox should receive the traceback text
                    mock_textbox.insert.assert_called_with("0.0", "test traceback")

                    # Button should be created
                    mock_btn_cls.assert_called_once()
                    args, kwargs = mock_btn_cls.call_args
                    assert "Show Details" in kwargs.get("text", "")

    def test_toggle_shows_and_hides(self, mock_ctk_app) -> None:
        """Toggle button should show/hide the traceback textbox."""
        with patch("main.ctk.CTkFrame"):
            with patch("main.ctk.CTkTextbox") as mock_textbox_cls:
                mock_textbox = MagicMock()
                # Initially hidden (not viewable)
                mock_textbox.winfo_viewable = MagicMock(side_effect=[False, True])
                mock_textbox_cls.return_value = mock_textbox

                with patch("main.ctk.CTkButton") as mock_btn_cls:
                    mock_btn = MagicMock()
                    mock_btn_cls.return_value = mock_btn

                    import main as main_module

                    mock_ctk_app._add_error_details = (
                        main_module.BBIMS_App._add_error_details.__get__(
                            mock_ctk_app, main_module.BBIMS_App
                        )
                    )
                    parent = MagicMock()
                    mock_ctk_app._add_error_details(parent, "traceback")

                    # Get the toggle function from the button command
                    toggle_fn = mock_btn_cls.call_args[1]["command"]

                    # First toggle: should show (pack)
                    toggle_fn()
                    mock_textbox.pack.assert_called_once_with(fill="x", pady=5)
                    mock_btn.configure.assert_called_with(text="📋 Hide Details")

                    # Second toggle: should hide (pack_forget)
                    toggle_fn()
                    mock_textbox.pack_forget.assert_called_once()
                    mock_btn.configure.assert_called_with(text="📋 Show Details")


# ---------- _install_global_exception_handler ----------


class TestGlobalExceptionHandler:
    """_install_global_exception_handler should hook sys.excepthook and report_callback_exception."""

    def test_sets_sys_excepthook(self, mock_ctk_app) -> None:
        """sys.excepthook should be replaced."""
        mock_ctk_app._install_global_exception_handler()
        assert sys.excepthook is not sys.__excepthook__

    def test_excepthook_calls_after(self, mock_ctk_app) -> None:
        """The excepthook handler should schedule show_error_dialog via after()."""
        mock_ctk_app._install_global_exception_handler()
        mock_ctk_app.after = MagicMock()
        mock_ctk_app.show_error_dialog = MagicMock()

        # Simulate an exception
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            sys.excepthook(exc_type, exc_value, exc_tb)

        # Should have called after(0, ...) to show the dialog on the main thread
        mock_ctk_app.after.assert_called_once()
        args, _ = mock_ctk_app.after.call_args
        assert args[0] == 0

    def test_excepthook_does_not_crash(self, mock_ctk_app) -> None:
        """The excepthook handler should not crash even if after() fails."""
        mock_ctk_app._install_global_exception_handler()
        mock_ctk_app.after = MagicMock(side_effect=Exception("after failed"))

        try:
            raise RuntimeError("Some error")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            # This should not raise
            sys.excepthook(exc_type, exc_value, exc_tb)

    def test_report_callback_exception_set(self, mock_ctk_app) -> None:
        """report_callback_exception should be set on the app."""
        mock_ctk_app._install_global_exception_handler()
        assert hasattr(mock_ctk_app, "report_callback_exception")
        assert callable(mock_ctk_app.report_callback_exception)


# ---------- _reset_app_state ----------


class TestResetAppState:
    """_reset_app_state should reset relevant state without crashing."""

    def test_resets_user_and_route(self, mock_ctk_app) -> None:
        """_reset_app_state should clear current_user and current_route."""
        mock_ctk_app.app_state.current_user = {"id": 1}
        mock_ctk_app.app_state.current_route = "dashboard"
        mock_ctk_app._reset_app_state()
        assert mock_ctk_app.app_state.current_user is None
        assert mock_ctk_app.app_state.current_route is None

    def test_stops_session_tracker(self, mock_ctk_app) -> None:
        """_reset_app_state should stop the session tracker if present."""
        mock_tracker = MagicMock()
        mock_ctk_app.session_tracker = mock_tracker
        mock_ctk_app._reset_app_state()
        mock_tracker.stop.assert_called_once()

    def test_handles_missing_session_tracker(self, mock_ctk_app) -> None:
        """_reset_app_state should not crash if session_tracker is not set."""
        mock_ctk_app.tk = None  # prevent Mock from faking hasattr
        mock_ctk_app._reset_app_state()  # Should not raise

    def test_stop_failure_does_not_crash(self, mock_ctk_app) -> None:
        """If session_tracker.stop() raises, _reset_app_state should continue."""
        mock_tracker = MagicMock()
        mock_tracker.stop.side_effect = Exception("Stop failed")
        mock_ctk_app.session_tracker = mock_tracker
        mock_ctk_app._reset_app_state()  # Should not raise
        assert mock_ctk_app.app_state.current_user is None


# ---------- _restart_from_error / _exit_from_error ----------


class TestRestartFromError:
    """_restart_from_error should clean up and return to landing page."""

    def test_restart_calls_reset_and_landing(self, mock_ctk_app) -> None:
        """_restart_from_error should reset state and show landing page."""
        mock_dialog = MagicMock()
        mock_ctk_app._reset_app_state = MagicMock()
        mock_ctk_app.clear_main_window = MagicMock()
        mock_ctk_app.show_landing_page = MagicMock()

        mock_ctk_app._restart_from_error(mock_dialog)

        mock_dialog.destroy.assert_called_once()
        mock_ctk_app._reset_app_state.assert_called_once()
        mock_ctk_app.clear_main_window.assert_called_once()
        mock_ctk_app.show_landing_page.assert_called_once()


class TestExitFromError:
    """_exit_from_error should close dialog and quit."""

    def test_exit_destroys_dialog_and_quits(self, mock_ctk_app) -> None:
        """_exit_from_error should destroy the dialog and call quit()."""
        mock_dialog = MagicMock()
        mock_ctk_app._exit_from_error(mock_dialog)

        mock_dialog.destroy.assert_called_once()
        mock_ctk_app.quit.assert_called_once()


# ---------- Error dialog integration via mock ----------


class TestNavigateErrorDialog:
    """When navigate() encounters an import failure, it should call show_error_dialog."""

    def test_safe_import_error_shows_dialog_on_failure(self, mock_ctk_app) -> None:
        """_safe_import should call after() to schedule show_error_dialog on failure."""
        mock_ctk_app.after = MagicMock()
        result = mock_ctk_app._safe_import("modules.definitely_not_real", "Nope")
        assert result is None
        mock_ctk_app.after.assert_called_once()
        assert mock_ctk_app.after.call_args[0][0] == 0

    def test_navigate_calls_show_error_dialog_on_instantiation_failure(self, mock_ctk_app) -> None:
        """When module_class raises during construction, navigate should show error dialog."""
        mock_ctk_app.app_state.current_route = "settings"
        mock_ctk_app.show_error_dialog = MagicMock()

        class BrokenModule:
            def __init__(self, *args, **kwargs):
                raise ValueError("Broken!")

        mock_ctk_app.get_module_class = MagicMock(return_value=BrokenModule)
        mock_ctk_app.navigate("some_route")

        mock_ctk_app.show_error_dialog.assert_called_once()
        args, _ = mock_ctk_app.show_error_dialog.call_args
        assert "Broken" in args[0] or "broken" in args[0].lower()
        # Route should be restored
        assert mock_ctk_app.app_state.current_route == "settings"
