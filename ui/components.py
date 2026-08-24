import customtkinter as ctk
from tkinter import TclError


class KPICard(ctk.CTkFrame):
    def __init__(self, master, title, value, icon="📊", color="#3b82f6", *args, **kwargs) -> None:
        super().__init__(
            master,
            corner_radius=10,
            fg_color="transparent",
            border_width=2,
            border_color=color,
            *args,
            **kwargs,
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        ctk.CTkLabel(header_frame, text=title, text_color="gray", font=ctk.CTkFont(size=14)).pack(
            side="left"
        )
        ctk.CTkLabel(header_frame, text=icon, font=ctk.CTkFont(size=20)).pack(side="right")

        self.val_lbl = ctk.CTkLabel(self, text=str(value), font=ctk.CTkFont(size=28, weight="bold"))
        self.val_lbl.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 15))

    def set_value(self, value) -> None:
        if self.winfo_exists():
            self.val_lbl.configure(text=str(value))


class SkeletonLoader(ctk.CTkFrame):
    def __init__(self, master, width=200, height=20, *args, **kwargs) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=5,
            fg_color=("gray80", "gray20"),
            *args,
            **kwargs,
        )
        self.pack_propagate(False)
        self._animating = True
        self._animate()

    def _animate(self) -> None:
        if not self.winfo_exists() or not getattr(self, "_animating", True):
            return
        try:
            current = self.cget("fg_color")
            if current == ("gray80", "gray20"):
                self.configure(fg_color=("gray75", "gray25"))
            else:
                self.configure(fg_color=("gray80", "gray20"))
        except (TclError, ValueError, TypeError):
            pass
        self.after(500, self._animate)

    def stop(self) -> None:
        self._animating = False
