"""Error dialog UI components for the IMS application."""

from __future__ import annotations

import customtkinter as ctk


def show_error_dialog(parent, friendly_msg: str, full_traceback: str | None = None, theme=None) -> None:
    """Show a friendly error dialog with options to restart or exit."""
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Unexpected Error")
    dialog.geometry("520x320")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.grab_set()
    dialog.focus()

    # Center on parent window
    dialog.update_idletasks()
    try:
        x = parent.winfo_rootx() + (parent.winfo_width() - 520) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 320) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
    except (ValueError, TypeError):
        pass

    frame = ctk.CTkFrame(dialog, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=25, pady=20)

    ctk.CTkLabel(frame, text="⚠️", font=ctk.CTkFont(size=40)).pack(pady=(5, 5))
    ctk.CTkLabel(frame, text="Something went wrong", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0, 5))
    ctk.CTkLabel(frame, text=str(friendly_msg), text_color="gray", wraplength=460, justify="center").pack(pady=(0, 12))

    accent = getattr(theme, "accent_color", "#89b4fa") if theme else "#89b4fa"
    danger = getattr(theme, "danger_color", "#f38ba8") if theme else "#f38ba8"

    btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
    btn_frame.pack(pady=5)

    def _restart():
        dialog.destroy()
        parent._reset_app_state()
        parent.clear_main_window()
        parent.show_landing_page()

    def _exit():
        dialog.destroy()
        parent.quit()

    ctk.CTkButton(btn_frame, text="🔄 Restart", command=_restart, fg_color=accent, width=120).pack(side="left", padx=6)
    ctk.CTkButton(btn_frame, text="✕ Exit", command=_exit, fg_color=danger, width=120).pack(side="left", padx=6)

    if full_traceback:
        _add_error_details(frame, full_traceback)


def _add_error_details(parent, traceback_text: str) -> None:
    """Add a collapsible traceback section to the error dialog."""
    details_frame = ctk.CTkFrame(parent, fg_color="transparent")
    details_frame.pack(fill="x", pady=(8, 0))

    tracebox = ctk.CTkTextbox(details_frame, height=80, fg_color=("gray90", "gray10"))
    tracebox.insert("0.0", traceback_text)
    tracebox.configure(state="disabled")

    def toggle():
        if tracebox.winfo_viewable():
            tracebox.pack_forget()
            toggle_btn.configure(text="📋 Show Details")
        else:
            tracebox.pack(fill="x", pady=5)
            toggle_btn.configure(text="📋 Hide Details")

    toggle_btn = ctk.CTkButton(details_frame, text="📋 Show Details", command=toggle, width=130, fg_color="gray", height=28)
    toggle_btn.pack()
