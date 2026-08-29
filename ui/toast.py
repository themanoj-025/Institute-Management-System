from tkinter import TclError

import customtkinter as ctk

TOAST_STYLES = {
    "success": {"bg": "#a6e3a1", "text": "#1e1e2e", "icon": "✔", "border": "#50fa7b"},
    "error": {"bg": "#f38ba8", "text": "#1e1e2e", "icon": "⚠", "border": "#ff5555"},
    "warning": {"bg": "#fab387", "text": "#1e1e2e", "icon": "▲", "border": "#ffb86c"},
    "info": {"bg": "#89b4fa", "text": "#1e1e2e", "icon": "ℹ", "border": "#8be9fd"},
}


class ToastInstance:
    def __init__(self, root, manager, message, type_name="info", duration=3000) -> None:
        self.root = root
        self.manager = manager
        self.style = TOAST_STYLES.get(type_name, TOAST_STYLES["info"])
        self.duration = duration

        self.toplevel = ctk.CTkToplevel(root)
        self.toplevel.overrideredirect(True)
        self.toplevel.attributes("-topmost", True)

        # Color bar left (represented by frame styling)
        self.main_frame = ctk.CTkFrame(self.toplevel, fg_color=self.style["bg"], corner_radius=6)
        self.main_frame.pack(fill="both", expand=True)

        # Left Accent Stripe
        self.left_stripe = ctk.CTkFrame(
            self.main_frame, fg_color=self.style["border"], width=6, height=40
        )
        self.left_stripe.pack(side="left", fill="y", padx=(0, 10))

        # Icon Label
        self.icon_lbl = ctk.CTkLabel(
            self.main_frame,
            text=self.style["icon"],
            text_color=self.style["text"],
            font=("Inter", 16, "bold"),
        )
        self.icon_lbl.pack(side="left", padx=5)

        # Message Label
        self.msg_lbl = ctk.CTkLabel(
            self.main_frame,
            text=message,
            text_color=self.style["text"],
            font=("Inter", 13),
            justify="left",
            anchor="w",
        )
        self.msg_lbl.pack(side="left", fill="x", expand=True, padx=10)

        # Close Button
        self.close_btn = ctk.CTkButton(
            self.main_frame,
            text="×",
            width=20,
            height=20,
            fg_color="transparent",
            hover_color=self.style["border"],
            text_color=self.style["text"],
            font=("Inter", 16, "bold"),
            command=self.dismiss,
        )
        self.close_btn.pack(side="right", padx=10)

        # Progress Bar at bottom
        self.progress_frame = ctk.CTkFrame(self.toplevel, fg_color=self.style["border"], height=3)
        self.progress_frame.pack(side="bottom", fill="x")

        self.toplevel.update_idletasks()
        self.width = 320
        self.height = 50

        # Initial position offscreen right
        self.target_y = 0
        self.current_x = 99999  # Far off-screen initially

    def position_and_slide(self, target_y) -> None:
        self.target_y = target_y

        # Safely get root window dimensions
        try:
            if not self.root.winfo_exists():
                self.dismiss()
                return
            final_x = self.root.winfo_rootx() + self.root.winfo_width() - self.width - 20
            if self.current_x == 99999:
                self.current_x = final_x + 300  # Start off-screen right
        except (TclError, RuntimeError):
            final_x = 100
            if self.current_x == 99999:
                self.current_x = final_x + 300

        try:
            self.toplevel.geometry(f"{self.width}x{self.height}+{self.current_x}+{self.target_y}")
        except (TclError, RuntimeError):
            self.dismiss()
            return

        # Slide in animation
        def slide_step() -> None:
            if not self.toplevel.winfo_exists():
                return
            if self.current_x > final_x:
                self.current_x -= 30
                if self.current_x < final_x:
                    self.current_x = final_x
                try:
                    self.toplevel.geometry(f"+{int(self.current_x)}+{int(self.target_y)}")
                except (TclError, RuntimeError):
                    pass
                self.toplevel.after(10, slide_step)
            else:
                self.animate_progress(self.duration)

        slide_step()

    def animate_progress(self, remaining) -> None:
        if not self.toplevel.winfo_exists():
            return
        if remaining <= 0:
            self.dismiss()
        else:
            fraction = max(0, remaining / self.duration)
            new_width = int(self.width * fraction)
            try:
                self.progress_frame.configure(width=new_width)
            except (TclError, RuntimeError):
                pass
            self.toplevel.after(50, lambda: self.animate_progress(remaining - 50))

    def dismiss(self) -> None:
        try:
            if self.toplevel.winfo_exists():
                self.toplevel.destroy()
        except (TclError, RuntimeError):
            pass
        self.manager.remove_toast(self)


class ToastManager:
    _instances: list["ToastInstance"] = []

    @classmethod
    def show(cls, root, message, type="info", duration=3000) -> None:
        # Create a new toast
        toast = ToastInstance(root, cls, message, type, duration)

        # If we have too many, dismiss the oldest
        if len(cls._instances) >= 4:
            oldest = cls._instances.pop(0)
            oldest.dismiss()

        cls._instances.append(toast)
        cls.reposition_all(root)

    @classmethod
    def remove_toast(cls, toast) -> None:
        if toast in cls._instances:
            cls._instances.remove(toast)
            if len(cls._instances) > 0:
                cls.reposition_all(toast.root)

    @classmethod
    def reposition_all(cls, root) -> None:
        start_y = root.winfo_rooty() + root.winfo_height() - 80
        for idx, inst in enumerate(reversed(cls._instances)):
            target_y = start_y - (idx * 58)
            inst.position_and_slide(target_y)

    @classmethod
    def clear_all(cls) -> None:
        for inst in list(cls._instances):
            inst.dismiss()
        cls._instances.clear()
