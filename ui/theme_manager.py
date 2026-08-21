import json
import os

import customtkinter as ctk

THEMES = {
    "dark": {
        "appearance": "dark",
        "base": "#1e1e2e",
        "surface": "#181825",
        "text": "#cdd6f4",
        "accent": "#89b4fa",
        "success": "#a6e3a1",
        "warning": "#fab387",
        "danger": "#f38ba8",
        "info": "#89b4fa",
    },
    "light": {
        "appearance": "light",
        "base": "#eff1f5",
        "surface": "#ffffff",
        "text": "#4c4f69",
        "accent": "#1e66f5",
        "success": "#40a02b",
        "warning": "#df8e1d",
        "danger": "#d20f39",
        "info": "#1e66f5",
    },
    "mocha": {
        "appearance": "dark",
        "base": "#1e1e2e",
        "surface": "#181825",
        "text": "#cdd6f4",
        "accent": "#cba6f7",  # purple
        "success": "#a6e3a1",
        "warning": "#fab387",
        "danger": "#f38ba8",
        "info": "#89b4fa",
    },
    "latte": {
        "appearance": "light",
        "base": "#eff1f5",
        "surface": "#ffffff",
        "text": "#4c4f69",
        "accent": "#8839ef",  # purple
        "success": "#40a02b",
        "warning": "#df8e1d",
        "danger": "#d20f39",
        "info": "#1e66f5",
    },
}

ACCENT_COLORS = {
    "blue": "#89b4fa",
    "purple": "#cba6f7",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "amber": "#fab387",
    "teal": "#94e2d5",
}


class ThemeManager:
    def __init__(self, root) -> None:
        self.root = root
        self.current_theme_name = "dark"
        self.current_accent_name = "blue"

        # Default colors
        self.accent_color = THEMES["dark"]["accent"]
        self.success_color = THEMES["dark"]["success"]
        self.warning_color = THEMES["dark"]["warning"]
        self.danger_color = THEMES["dark"]["danger"]
        self.info_color = THEMES["dark"]["info"]

        # Typography
        self.header_size = 24
        self.main_size = 14
        self.small_size = 12

        self.header_font = ctk.CTkFont(family="Inter", size=self.header_size, weight="bold")
        self.main_font = ctk.CTkFont(family="Inter", size=self.main_size)
        self.small_font = ctk.CTkFont(family="Inter", size=self.small_size)

        self.load_settings()

    def load_settings(self) -> None:
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database",
            "settings.json",
        )
        try:
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    settings = json.load(f)
                    theme = settings.get("theme", "dark")
                    accent = settings.get("accent", "blue")
                    font_size = settings.get("font_size", 14)

                    self.current_theme_name = theme
                    self.current_accent_name = accent
                    self.main_size = font_size
                    self.small_size = font_size - 2
                    self.header_size = font_size + 10

                    self.apply(theme, save=False)
                    self.set_accent(accent, save=False)
                    self.set_font_size(font_size, save=False)
            else:
                self.apply("dark", save=False)
        except Exception:
            self.apply("dark", save=False)

    def save_settings(self) -> None:
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database",
            "settings.json",
        )
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        settings = {
            "theme": self.current_theme_name,
            "accent": self.current_accent_name,
            "font_size": self.main_size,
        }
        try:
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception:
            pass

    def apply(self, theme_name: str, save: bool = True) -> None:
        if theme_name not in THEMES:
            return
        self.current_theme_name = theme_name
        theme = THEMES[theme_name]

        ctk.set_appearance_mode(theme["appearance"])
        self.accent_color = theme["accent"]
        self.success_color = theme["success"]
        self.warning_color = theme["warning"]
        self.danger_color = theme["danger"]
        self.info_color = theme["info"]

        # Recolor
        self._recursive_recolor(self.root, theme)

        if save:
            self.save_settings()

    def set_accent(self, color_name: str, save: bool = True) -> None:
        if color_name not in ACCENT_COLORS:
            return
        self.current_accent_name = color_name
        accent_hex = ACCENT_COLORS[color_name]

        theme = THEMES[self.current_theme_name].copy()
        theme["accent"] = accent_hex
        self.accent_color = accent_hex

        self._recursive_recolor(self.root, theme)

        if save:
            self.save_settings()

    def set_font_size(self, size: int, save: bool = True) -> None:
        self.main_size = size
        self.small_size = max(10, size - 2)
        self.header_size = size + 10

        self.header_font.configure(size=self.header_size)
        self.main_font.configure(size=self.main_size)
        self.small_font.configure(size=self.small_size)

        self._recursive_resize(self.root)

        if save:
            self.save_settings()

    def _recursive_recolor(self, widget, theme) -> None:
        # Configure the widget itself if it supports colors
        try:
            if isinstance(widget, ctk.CTkFrame):
                widget.configure(
                    fg_color=theme["base"] if widget == self.root else theme["surface"]
                )
            elif isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=theme["text"])
            elif isinstance(widget, ctk.CTkButton):
                widget.configure(fg_color=theme["accent"], hover_color=theme["info"])
            elif isinstance(widget, ctk.CTkEntry) or isinstance(widget, ctk.CTkTextbox):
                widget.configure(
                    fg_color=theme["surface"],
                    border_color=theme["accent"],
                    text_color=theme["text"],
                )
            elif isinstance(widget, ctk.CTkOptionMenu) or isinstance(
                widget, ctk.CTkSegmentedButton
            ):
                widget.configure(fg_color=theme["surface"], selected_color=theme["accent"])
            elif isinstance(widget, ctk.CTkSwitch):
                widget.configure(progress_color=theme["accent"])
        except Exception:
            pass

        # Walk children
        try:
            for child in widget.winfo_children():
                self._recursive_recolor(child, theme)
        except Exception:
            pass

    def _recursive_resize(self, widget) -> None:
        try:
            if isinstance(widget, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry, ctk.CTkTextbox)):
                try:
                    current_font = widget.cget("font")
                    if current_font:
                        font_str = (
                            str(current_font).lower() if not hasattr(current_font, "cget") else ""
                        )
                        if "bold" in font_str:
                            widget.configure(font=self.header_font)
                        else:
                            widget.configure(font=self.main_font)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            for child in widget.winfo_children():
                self._recursive_resize(child)
        except Exception:
            pass
