import customtkinter as ctk

from ui.toast import ToastManager


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm

        ctk.CTkLabel(self, text="Settings", font=self.tm.header_font).pack(pady=20, anchor="w")
        ctk.CTkLabel(
            self,
            text="Customize your experience and configure system settings.",
            font=self.tm.main_font,
            text_color="gray",
        ).pack(anchor="w")

        tabview = ctk.CTkTabview(self)
        tabview.pack(fill="both", expand=True, pady=(10, 0))

        # --- Appearance ---
        t_appearance = tabview.add("🎨 Appearance")

        theme_card = ctk.CTkFrame(t_appearance, corner_radius=8)
        theme_card.pack(fill="x", pady=15, padx=15)

        ctk.CTkLabel(theme_card, text="Theme Mode", font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=15, pady=(15, 5)
        )
        ctk.CTkLabel(
            theme_card,
            text="Choose between light, dark, or system default.",
            text_color="gray",
        ).pack(anchor="w", padx=15)

        self.theme_var = ctk.StringVar(value=ctk.get_appearance_mode().capitalize())
        theme_seg = ctk.CTkSegmentedButton(
            theme_card,
            values=["Light", "Dark", "System"],
            variable=self.theme_var,
            command=self._change_theme,
        )
        theme_seg.pack(pady=(10, 15))

        # Accent color card
        accent_card = ctk.CTkFrame(t_appearance, corner_radius=8)
        accent_card.pack(fill="x", pady=15, padx=15)

        ctk.CTkLabel(
            accent_card, text="Accent Color", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        from ui.theme_manager import ACCENT_COLORS

        accent_frame = ctk.CTkFrame(accent_card, fg_color="transparent")
        accent_frame.pack(pady=(10, 15))

        self.accent_var = ctk.StringVar(value=self.tm.current_accent_name)
        for i, (name, hex_color) in enumerate(ACCENT_COLORS.items()):
            btn = ctk.CTkButton(
                accent_frame,
                text=name.capitalize(),
                width=80,
                height=32,
                fg_color=hex_color,
                hover_color=hex_color,
                text_color="#1e1e2e",
                command=lambda n=name: self._set_accent(n),
            )
            btn.grid(row=0, column=i, padx=4)

        # --- SMTP ---
        t_smtp = tabview.add("📧 SMTP")

        smtp_card = ctk.CTkFrame(t_smtp, corner_radius=8)
        smtp_card.pack(fill="x", pady=15, padx=15)

        ctk.CTkLabel(
            smtp_card,
            text="Email Configuration",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 5))

        items = [
            ("Host", "smtp.gmail.com"),
            ("Port", "587"),
            ("Username", "admin@bb.edu.in"),
        ]
        for label, val in items:
            row = ctk.CTkFrame(smtp_card, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=val, text_color="gray").pack(side="left")

        ctk.CTkLabel(smtp_card, text="", height=10).pack()

        # --- Institute Info ---
        t_institute = tabview.add("🏛️ Institute")
        ctk.CTkLabel(
            t_institute,
            text="Institute profile and branding settings.",
            text_color="gray",
        ).pack(pady=20)
        ctk.CTkLabel(
            t_institute,
            text="Binary Brain Institute of Technology",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack()

        # --- Backup/Restore ---
        t_backup = tabview.add("💾 Backup")
        backup_card = ctk.CTkFrame(t_backup, corner_radius=8)
        backup_card.pack(fill="x", pady=15, padx=15)
        ctk.CTkLabel(
            backup_card,
            text="Database Backup & Restore",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(15, 5))

        btn_frame = ctk.CTkFrame(backup_card, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="📥 Download Backup", width=160, height=38).pack(
            side="left", padx=5
        )
        ctk.CTkButton(btn_frame, text="📤 Restore from File", width=160, height=38).pack(
            side="left", padx=5
        )

        # --- Advanced ---
        t_advanced = tabview.add("⚙ Advanced")
        ctk.CTkLabel(t_advanced, text="Advanced system configuration.", text_color="gray").pack(
            pady=20
        )

    def _change_theme(self, value):
        theme_map = {"Light": "light", "Dark": "dark", "System": "dark"}
        theme_name = theme_map.get(value, "dark")
        self.tm.apply(theme_name)
        ToastManager.show(self.winfo_toplevel(), f"Theme set to {value} ✅", "success")

    def _set_accent(self, name):
        self.tm.set_accent(name)
        ToastManager.show(
            self.winfo_toplevel(),
            f"Accent color set to {name.capitalize()} ✅",
            "success",
        )
