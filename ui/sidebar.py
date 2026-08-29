import json
import os
from tkinter import TclError

import customtkinter as ctk

ROUTE_ICONS = {
    "dashboard": "📊",
    "manage_students": "🎓",
    "manage_staff": "👥",
    "manage_courses": "📖",
    "manage_subjects": "🔬",
    "leave_manager": "✉",
    "fee_management": "💳",
    "notice_board": "📢",
    "activity_logs": "📜",
    "attendance_taker": "✍",
    "result_manager": "📝",
    "notice_viewer": "📢",
    "leave_apply": "✉",
    "feedback_sender": "💬",
    "profile": "👤",
    "settings": "⚙",
    "enquiry_manager": "📬",
    "logout": "🚪",
}


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, theme_manager, navigate_callback, role, *args, **kwargs) -> None:
        super().__init__(master, width=220, corner_radius=0, *args, **kwargs)
        self.tm = theme_manager
        self.navigate_callback = navigate_callback
        self.role = role

        self.pack_propagate(False)  # Prevent shrinking
        self._collapsed = False
        self._animating = False
        self.buttons = []
        self._tooltip = None

        # Load collapse state from settings
        self.load_settings()

        self.grid_rowconfigure(9, weight=1)  # Spacer

        # Upper Toggle Button
        self.toggle_btn = ctk.CTkButton(
            self,
            text="☰",
            width=35,
            height=35,
            fg_color="transparent",
            text_color=("black", "white"),
            font=("Inter", 16, "bold"),
            command=self.toggle,
        )
        self.toggle_btn.pack(anchor="ne", padx=10, pady=10)

        # Avatar Area
        self.avatar_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.avatar_frame.pack(fill="x", padx=10, pady=10)

        self.avatar_circle = ctk.CTkFrame(
            self.avatar_frame,
            width=40,
            height=40,
            corner_radius=20,
            fg_color=self.tm.accent_color,
        )
        self.avatar_circle.pack(pady=5)
        self.avatar_circle.pack_propagate(False)

        initials = role[:2].upper()
        self.avatar_txt = ctk.CTkLabel(
            self.avatar_circle,
            text=initials,
            font=("Inter", 14, "bold"),
            text_color="#1e1e2e",
        )
        self.avatar_txt.pack(expand=True)

        self.name_lbl = ctk.CTkLabel(
            self.avatar_frame, text=role.capitalize(), font=("Inter", 13, "bold")
        )
        self.name_lbl.pack()

        # Menu Scrollable Container
        self.menu_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.menu_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Menus based on role
        self.menus = {
            "admin": [
                ("Dashboard", "dashboard"),
                ("Manage Students", "manage_students"),
                ("Manage Staff", "manage_staff"),
                ("Manage Courses", "manage_courses"),
                ("Manage Subjects", "manage_subjects"),
                ("Leave Manager", "leave_manager"),
                ("Fee Management", "fee_management"),
                ("Notice Board", "notice_board"),
                ("Activity Logs", "activity_logs"),
                ("Enquiry Manager", "enquiry_manager"),
            ],
            "staff": [
                ("Dashboard", "dashboard"),
                ("Take Attendance", "attendance_taker"),
                ("Enter Results", "result_manager"),
                ("Notice Board", "notice_viewer"),
                ("Apply Leave", "leave_apply"),
                ("Send Feedback", "feedback_sender"),
                ("My Profile", "profile"),
            ],
            "student": [
                ("Dashboard", "dashboard"),
                ("View Attendance", "view_attendance"),
                ("View Result", "view_result"),
                ("Notice Board", "notice_viewer"),
                ("Apply Leave", "leave_apply"),
                ("Send Feedback", "feedback_sender"),
                ("My Profile", "profile"),
            ],
        }

        self.build_menu()

        # Bind resize monitor on the actual toplevel window
        self._top_level = self.winfo_toplevel()
        self._top_level.bind("<Configure>", self.on_window_configure, add="+")

    def load_settings(self) -> None:
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database",
            "settings.json",
        )
        if os.path.exists(settings_path):
            try:
                with open(settings_path) as f:
                    settings = json.load(f)
                    self._collapsed = settings.get("sidebar_collapsed", False)
                    if self._collapsed:
                        self.configure(width=64)
                    else:
                        self.configure(width=220)
            except (TclError, RuntimeError):
                pass

    def save_settings(self) -> None:
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database",
            "settings.json",
        )
        try:
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path) as f:
                    settings = json.load(f)
            settings["sidebar_collapsed"] = self._collapsed
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
        except (OSError, json.JSONDecodeError):
            pass

    def build_menu(self) -> None:
        # Clear existing
        for b in self.buttons:
            b.destroy()
        self.buttons.clear()

        role_menu = self.menus.get(self.role, [])
        for label, route in role_menu:
            icon = ROUTE_ICONS.get(route, "🔹")

            btn = ctk.CTkButton(
                self.menu_frame,
                text=f"{icon}  {label}" if not self._collapsed else icon,
                fg_color="transparent",
                text_color=("black", "white"),
                anchor="w" if not self._collapsed else "center",
                hover_color=self.tm.accent_color,
                command=lambda r=route: self.navigate(r),
            )
            btn.pack(fill="x", padx=5, pady=4)
            self.buttons.append(btn)

            # Tooltip trigger if collapsed
            if self._collapsed:
                btn.bind("<Enter>", lambda e, lbl=label: self.show_tooltip(e, lbl))
                btn.bind("<Leave>", self.hide_tooltip)

        # Bottom items
        settings_btn = ctk.CTkButton(
            self,
            text=(
                f"{ROUTE_ICONS['settings']}  Settings"
                if not self._collapsed
                else ROUTE_ICONS["settings"]
            ),
            fg_color="transparent",
            text_color=("black", "white"),
            anchor="w" if not self._collapsed else "center",
            command=lambda: self.navigate("settings"),
        )
        settings_btn.pack(side="bottom", fill="x", padx=5, pady=5)
        self.buttons.append(settings_btn)

        logout_btn = ctk.CTkButton(
            self,
            text=(
                f"{ROUTE_ICONS['logout']}  Logout" if not self._collapsed else ROUTE_ICONS["logout"]
            ),
            fg_color="transparent",
            text_color=("black", "white"),
            anchor="w" if not self._collapsed else "center",
            hover_color=self.tm.danger_color,
            command=lambda: self.navigate("logout"),
        )
        logout_btn.pack(side="bottom", fill="x", padx=5, pady=5)
        self.buttons.append(logout_btn)

    def show_tooltip(self, event, text) -> None:
        self.hide_tooltip()
        self._tooltip = ctk.CTkToplevel(self)
        self._tooltip.overrideredirect(True)
        self._tooltip.attributes("-topmost", True)

        lbl = ctk.CTkLabel(
            self._tooltip,
            text=text,
            fg_color=self.tm.info_color,
            text_color="white",
            corner_radius=4,
            padx=8,
            pady=4,
        )
        lbl.pack()

        # Position right of cursor
        x = event.x_root + 15
        y = event.y_root + 10
        self._tooltip.geometry(f"+{x}+{y}")

    def hide_tooltip(self, event=None) -> None:
        if self._tooltip:
            try:
                self._tooltip.destroy()
            except (TclError, RuntimeError):
                pass
            self._tooltip = None

    def navigate(self, route) -> None:
        if self._animating:
            return
        self.navigate_callback(route)

    def toggle(self) -> None:
        if self._animating:
            return
        self._collapsed = not self._collapsed
        self._animating = True

        # Disable buttons during animation
        for b in self.buttons:
            b.configure(state="disabled")

        target_width = 64 if self._collapsed else 220
        self._animate_step(target_width)

    def _animate_step(self, target_width) -> None:
        current_width = self.winfo_width()
        step = 8 if current_width < target_width else -8

        next_width = current_width + step
        if (step > 0 and next_width >= target_width) or (step < 0 and next_width <= target_width):
            self.configure(width=target_width)
            self._animating = False
            # Reenable and rebuild layout
            for b in self.buttons:
                b.configure(state="normal")

            # Hide names if collapsed
            if self._collapsed:
                self.name_lbl.pack_forget()
            else:
                self.name_lbl.pack()

            self.build_menu()
            self.save_settings()
        else:
            self.configure(width=next_width)
            self.after(12, lambda: self._animate_step(target_width))

    def on_window_configure(self, event) -> None:
        if hasattr(event, "widget") and event.widget == self._top_level:
            # Auto-collapse at 900px breakpoint
            if event.width < 900 and not self._collapsed and not self._animating:
                self.toggle()
            elif event.width >= 900 and self._collapsed and not self._animating:
                self.toggle()
