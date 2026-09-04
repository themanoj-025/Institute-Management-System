"""BB IMS — Main application entry point."""

from __future__ import annotations

import importlib
import os
import traceback as tb_mod
from tkinter import TclError

import customtkinter as ctk

from auth.session import SessionTracker
from database.db_session import get_db, init_db
from database.seeder import seed_database
from error_dialog import show_error_dialog
from landing.landing_page import LandingPage
from routes import resolve_route
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
        self._install_global_exception_handler()

        from config.settings import init_app

        init_app()

        self.title("Binary Brain Institute Management System")
        self.geometry("1280x720")

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (1280 / 2)
        y = (screen_height / 2) - (720 / 2)
        self.geometry("%dx%d+%d+%d" % (1280, 720, x, y))
        self.minsize(1024, 768)

        self.tm = ThemeManager(self)
        self.app_state = AppState()
        self.db_session = next(get_db())

        self.bind("<Control-k>", lambda e: self.show_global_search())
        self.withdraw()

        self.loading = LoadingScreen(self, self.tm)
        self.loading.run_loading(self.on_loading_complete)

    def on_loading_complete(self) -> None:
        init_db()
        self.deiconify()
        self.show_landing_page()

        import threading

        def _seed_task():
            try:
                seed_database(self.db_session)
            except (OSError, ValueError) as e:
                log.error("Seeding failed: %s", e)

        t = threading.Thread(target=_seed_task, daemon=True)
        t.start()

    def show_landing_page(self) -> None:
        self.clear_main_window()
        self.landing = LandingPage(self, self.tm, self.app_state, self.db_session, self.start_main_app)
        self.landing.pack(fill="both", expand=True)

    def start_main_app(self) -> None:
        self.clear_main_window()
        self.session_tracker = SessionTracker(self.handle_logout, self)
        self.session_tracker.start()

        self.bind("<Any-KeyPress>", self.session_tracker.update_activity)
        self.bind("<Any-Button>", self.session_tracker.update_activity)
        self.bind("<Motion>", self.session_tracker.update_activity)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        role = self.app_state.current_user.get("role", "student")
        self.sidebar = Sidebar(self, self.tm, self.navigate, role)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

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

        module_class = self._resolve_module(route)
        if module_class:
            try:
                instance = module_class(self.content_area, self.tm, self.app_state, self.db_session)
                instance.pack(fill="both", expand=True)
            except (OSError, ValueError) as e:
                log.error("Failed to instantiate %s: %s\n%s", route, e, tb_mod.format_exc())
                self.show_error_dialog(f"Failed to open {route}: {e}", tb_mod.format_exc())
                self.app_state.current_route = self._prev_route
        else:
            self.app_state.current_route = self._prev_route

    def _resolve_module(self, route):
        """Resolve a route to its module class via routes.py mapping."""
        role = self.app_state.current_user.get("role", "student")
        resolved = resolve_route(route, role)
        if not resolved:
            return None
        module_path, class_name = resolved
        try:
            mod = importlib.import_module(module_path)
            return getattr(mod, class_name)
        except (OSError, ValueError) as e:
            log.error("Failed to import %s.%s: %s\n%s", module_path, class_name, e, tb_mod.format_exc())
            self.after(0, lambda: self.show_error_dialog(f"Failed to load module: {class_name}", tb_mod.format_exc()))
            return None

    def _install_global_exception_handler(self) -> None:
        app = self

        def _handler(exc_type, exc_value, exc_tb):
            full_tb = "".join(tb_module.format_exception(exc_type, exc_value, exc_tb))
            log.critical("Unhandled exception:\n%s", full_tb)
            try:
                app.after(0, lambda: app.show_error_dialog(str(exc_value), full_tb))
            except (TclError, RuntimeError):
                pass

        import traceback as tb_module

        self.report_callback_exception = _handler
        sys.excepthook = _handler

    def show_error_dialog(self, friendly_msg, full_traceback=None) -> None:
        show_error_dialog(self, friendly_msg, full_traceback, self.tm)

    def _reset_app_state(self) -> None:
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
