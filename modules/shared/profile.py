import customtkinter as ctk


class ProfileView(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state

        ctk.CTkLabel(self, text="My Profile", font=self.tm.header_font).pack(pady=20, anchor="w")

        # Avatar card
        avatar_card = ctk.CTkFrame(
            self, corner_radius=12, border_width=2, border_color=self.tm.accent_color
        )
        avatar_card.pack(fill="x", pady=10, padx=10)

        # Avatar circle
        user = app_state.current_user or {}
        name = user.get("name", "User")
        initials = "".join(w[0].upper() for w in name.split()[:2]) if name != "User" else "U"

        avatar_frame = ctk.CTkFrame(
            avatar_card,
            width=80,
            height=80,
            corner_radius=40,
            fg_color=self.tm.accent_color,
        )
        avatar_frame.pack(pady=(20, 10))
        avatar_frame.pack_propagate(False)
        ctk.CTkLabel(
            avatar_frame,
            text=initials,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#1e1e2e",
        ).pack(expand=True)

        ctk.CTkLabel(avatar_card, text=name, font=ctk.CTkFont(size=18, weight="bold")).pack()
        ctk.CTkLabel(
            avatar_card,
            text=user.get("role", "").capitalize(),
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(pady=(0, 15))

        # Info card
        info_frame = ctk.CTkFrame(self, corner_radius=10)
        info_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(
            info_frame, text="Account Details", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        details = [
            ("Username", user.get("username", "N/A")),
            ("Email", user.get("email", "N/A")),
            ("Role", user.get("role", "N/A").capitalize()),
        ]
        for label, value in details:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(
                row,
                text=label,
                font=ctk.CTkFont(size=13),
                text_color="gray",
                width=100,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(row, text=str(value), font=ctk.CTkFont(size=13), anchor="w").pack(
                side="left", fill="x", expand=True
            )

        ctk.CTkLabel(info_frame, text="", height=15).pack()

        # Action buttons
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.pack(fill="x", pady=10, padx=10)
        ctk.CTkButton(
            actions_frame,
            text="📸 Capture Photo (Webcam)",
            width=200,
            height=38,
            fg_color="gray",
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            actions_frame,
            text="🔑 Change Password",
            width=200,
            height=38,
            fg_color=self.tm.accent_color,
        ).pack(side="left", padx=5)
