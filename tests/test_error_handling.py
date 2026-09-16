"""
Unit tests for error handling in main.py and error_dialog.py:
- navigate() error recovery via _prev_route
- _resolve_module() import failure handling
- show_error_dialog() and related helpers
- _install_global_exception_handler()
- _reset_app_state()
"""

import sys
from collections.abc import Iterator
from typing import Any
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
def mock_ctk_app() -> Iterator[Any]:
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
        app._show_error_dialog_called = False
        app._last_error_msg = None
        app._last_error_tb = None
        app.tk = MagicMock()
        yield app

    # Restore sys.excepthook to avoid leaking to other tests
    sys.excepthook = original_excepthook


# ---------- _resolve_module ----------


class TestResolveModule:
    """_resolve_module should safely import modules and fail gracefully."""

    def test_import_valid_module(self, mock_ctk_app) -> None:
        """Importing a known-good module should return its class."""
        with patch("main.resolve_route", return_value=("services.auth_service", "AuthService")):
            cls = mock_ctk_app._resolve_module("dashboard")
        from services.auth_service import AuthService

        assert cls is AuthService
        mock_ctk_app.after.assert_not_called()  # No error dialog

    def test_import_nonexistent_module(self, mock_ctk_app) -> None:
        """Importing a non-existent module should return None and show error dialog."""
        with patch("main.resolve_route", return_value=("modules.nonexistent", "FakeClass")):
            cls = mock_ctk_app._resolve_module("whatever")
        assert cls is None
        # Should have scheduled an error dialog via after()
        mock_ctk_app.after.assert_called_once()
        args, _ = mock_ctk_app.after.call_args
        assert args[0] == 0  # Delay is 0

    def test_import_nonexistent_class(self, mock_ctk_app) -> None:
        """A module missing the expected class should return None and show error dialog."""
        with patch("main.resolve_route", return_value=("services.auth_service", "NoSuchClass")):
            cls = mock_ctk_app._resolve_module("whatever")
        assert cls is None
        mock_ctk_app.after.assert_called_once()
        args, _ = mock_ctk_app.after.call_args
        assert args[0] == 0

    def test_unknown_route_returns_none(self, mock_ctk_app) -> None:
        """An unmapped route should return None without scheduling a dialog."""
        assert mock_ctk_app._resolve_module("definitely_not_a_route") is None
        mock_ctk_app.after.assert_not_called()


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
        mock_ctk_app._resolve_module = MagicMock()  # Should NOT be called
        mock_ctk_app.navigate("dashboard")
        mock_ctk_app._resolve_module.assert_not_called()

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
        mock_ctk_app._resolve_module = MagicMock(return_value=DummyModule)
        mock_ctk_app.navigate("dashboard")
        assert mock_ctk_app._prev_route == "settings"
        assert mock_ctk_app.app_state.current_route == "dashboard"

    def test_navigate_module_import_failure(self, mock_ctk_app) -> None:
        """If module instantiation fails, navigate should restore _prev_route."""
        mock_ctk_app.app_state.current_route = "settings"

        # navigate() deliberately catches (OSError, ValueError) around instantiation
        class FailingModule:
            def __init__(self, *args, **kwargs):
                raise ValueError("Module init failed!")

        mock_ctk_app._resolve_module = MagicMock(return_value=FailingModule)
        mock_ctk_app.navigate("some_route")
        # Should restore to previous route
        assert mock_ctk_app.app_state.current_route == "settings"

    def test_navigate_clears_content_area(self, mock_ctk_app) -> None:
        """navigate() should destroy existing widgets in content_area."""
        children = [MagicMock() for _ in range(3)]
        mock_ctk_app.content_area.winfo_children = MagicMock(return_value=children)
        mock_ctk_app._resolve_module = MagicMock(return_value=None)
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
        mock_ctk_app._resolve_module = MagicMock(return_value=DummyModule)
        mock_ctk_app.navigate("profile")
        assert mock_ctk_app.app_state.current_route == "profile"


# ---------- show_error_dialog ----------


class TestErrorDialog:
    """Test show_error_dialog with mocked widgets."""

    def test_creates_dialog_with_correct_title(self, mock_ctk_app) -> None:
        """Dialog should have the correct title and attributes."""
        with patch("error_dialog.ctk") as mock_ctk:
            dialog = MagicMock()
            mock_ctk.CTkToplevel.return_value = dialog

            from error_dialog import show_error_dialog

            show_error_dialog(mock_ctk_app, "Test error message")

            dialog.title.assert_called_with("Unexpected Error")
            dialog.attributes.assert_called_with("-topmost", True)
            dialog.grab_set.assert_called_once()
            dialog.focus.assert_called_once()
            dialog.resizable.assert_called_with(False, False)

    def test_dialog_with_traceback_calls_add_details(self, mock_ctk_app) -> None:
        """When full_traceback is provided, _add_error_details should be called."""
        with (
            patch("error_dialog.ctk") as mock_ctk,
            patch("error_dialog._add_error_details") as mock_add,
        ):
            mock_ctk.CTkToplevel.return_value = MagicMock()

            from error_dialog import show_error_dialog

            show_error_dialog(mock_ctk_app, "Error", "Traceback line 1\nTraceback line 2")

            mock_add.assert_called_once()

    def test_dialog_without_traceback_skips_details(self, mock_ctk_app) -> None:
        """When full_traceback is None, _add_error_details should NOT be called."""
        with (
            patch("error_dialog.ctk") as mock_ctk,
            patch("error_dialog._add_error_details") as mock_add,
        ):
            mock_ctk.CTkToplevel.return_value = MagicMock()

            from error_dialog import show_error_dialog

            show_error_dialog(mock_ctk_app, "Error")

            mock_add.assert_not_called()


# ---------- _add_error_details ----------


class TestAddErrorDetails:
    """_add_error_details should create a collapsible traceback section."""

    def test_creates_toggle_button(self, mock_ctk_app) -> None:
        """_add_error_details should create a toggle button and a textbox."""
        with patch("error_dialog.ctk") as mock_ctk:
            textbox = MagicMock()
            textbox.winfo_viewable = MagicMock(return_value=False)
            mock_ctk.CTkTextbox.return_value = textbox
            mock_ctk.CTkButton.return_value = MagicMock()

            from error_dialog import _add_error_details

            _add_error_details(MagicMock(), "test traceback")

            # Textbox should receive the traceback text
            textbox.insert.assert_called_with("0.0", "test traceback")

            # Button should be created
            mock_ctk.CTkButton.assert_called_once()
            assert "Show Details" in mock_ctk.CTkButton.call_args[1].get("text", "")

    def test_toggle_shows_and_hides(self, mock_ctk_app) -> None:
        """Toggle button should show/hide the traceback textbox."""
        with patch("error_dialog.ctk") as mock_ctk:
            textbox = MagicMock()
            # Initially hidden (not viewable)
            textbox.winfo_viewable = MagicMock(side_effect=[False, True])
            mock_ctk.CTkTextbox.return_value = textbox
            toggle_btn = MagicMock()
            mock_ctk.CTkButton.return_value = toggle_btn

            from error_dialog import _add_error_details

            _add_error_details(MagicMock(), "traceback")

            # Get the toggle function from the button command
            toggle_fn = mock_ctk.CTkButton.call_args[1]["command"]

            # First toggle: should show (pack)
            toggle_fn()
            textbox.pack.assert_called_once_with(fill="x", pady=5)
            toggle_btn.configure.assert_called_with(text="📋 Hide Details")

            # Second toggle: should hide (pack_forget)
            toggle_fn()
            textbox.pack_forget.assert_called_once()
            toggle_btn.configure.assert_called_with(text="📋 Show Details")


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
        mock_ctk_app.after = MagicMock(side_effect=RuntimeError("after failed"))

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
        mock_tracker.stop.side_effect = RuntimeError("Stop failed")
        mock_ctk_app.session_tracker = mock_tracker
        mock_ctk_app._reset_app_state()  # Should not raise
        assert mock_ctk_app.app_state.current_user is None


# ---------- Error dialog restart / exit actions ----------


class TestErrorDialogActions:
    """The dialog's Restart and Exit buttons should clean up correctly."""

    def test_restart_calls_reset_and_landing(self, mock_ctk_app) -> None:
        """Restart should destroy the dialog, reset state, and show the landing page."""
        with patch("error_dialog.ctk") as mock_ctk:
            dialog = MagicMock()
            mock_ctk.CTkToplevel.return_value = dialog

            from error_dialog import show_error_dialog

            mock_ctk_app._reset_app_state = MagicMock()
            mock_ctk_app.clear_main_window = MagicMock()
            mock_ctk_app.show_landing_page = MagicMock()

            show_error_dialog(mock_ctk_app, "boom")

            restart_cmd = mock_ctk.CTkButton.call_args_list[0][1]["command"]
            restart_cmd()

            dialog.destroy.assert_called_once()
            mock_ctk_app._reset_app_state.assert_called_once()
            mock_ctk_app.clear_main_window.assert_called_once()
            mock_ctk_app.show_landing_page.assert_called_once()

    def test_exit_destroys_dialog_and_quits(self, mock_ctk_app) -> None:
        """Exit should destroy the dialog and call quit()."""
        with patch("error_dialog.ctk") as mock_ctk:
            dialog = MagicMock()
            mock_ctk.CTkToplevel.return_value = dialog

            from error_dialog import show_error_dialog

            show_error_dialog(mock_ctk_app, "boom")

            exit_cmd = mock_ctk.CTkButton.call_args_list[1][1]["command"]
            exit_cmd()

            dialog.destroy.assert_called_once()
            mock_ctk_app.quit.assert_called_once()


# ---------- Error dialog integration via mock ----------


class TestNavigateErrorDialog:
    """When navigate() encounters an import failure, it should call show_error_dialog."""

    def test_import_error_schedules_dialog(self, mock_ctk_app) -> None:
        """_resolve_module should call after() to schedule show_error_dialog on failure."""
        mock_ctk_app.after = MagicMock()
        with patch("main.resolve_route", return_value=("modules.definitely_not_real", "Nope")):
            result = mock_ctk_app._resolve_module("whatever")
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

        mock_ctk_app._resolve_module = MagicMock(return_value=BrokenModule)
        mock_ctk_app.navigate("some_route")

        mock_ctk_app.show_error_dialog.assert_called_once()
        args, _ = mock_ctk_app.show_error_dialog.call_args
        assert "Broken" in args[0] or "broken" in args[0].lower()
        # Route should be restored
        assert mock_ctk_app.app_state.current_route == "settings"
