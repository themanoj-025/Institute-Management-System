import customtkinter as ctk


class LoadingScreen(ctk.CTkToplevel):
    def __init__(self, master, tm, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.tm = tm
        self.title("Loading...")

        # Make it full screen / no borders
        self.overrideredirect(True)
        width = 400
        height = 300
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.configure(fg_color=("white", "gray10"))

        # Arc progress / Logo animation setup
        self.logo_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=36, weight="bold"))
        self.logo_lbl.pack(expand=True)

        self.progress = ctk.CTkProgressBar(self, width=300, progress_color=tm.accent_color)
        self.progress.pack(pady=20)
        self.progress.set(0)

    def run_loading(self, on_complete):
        target_text = "BINARY BRAIN"
        self.char_idx = 0
        self.on_complete = on_complete
        self._animate_text(target_text)

    def _animate_text(self, text):
        if self.char_idx < len(text):
            current = self.logo_lbl.cget("text")
            self.logo_lbl.configure(text=current + text[self.char_idx])
            self.progress.set((self.char_idx + 1) / len(text))
            self.char_idx += 1
            # Total ~2.5s -> 2500ms / len(text)
            self.after(2500 // len(text), lambda: self._animate_text(text))
        else:
            self.after(500, self._finish)

    def _finish(self):
        self.destroy()
        if self.on_complete:
            self.on_complete()
