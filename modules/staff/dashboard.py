import customtkinter as ctk

from ui.components import KPICard


class StaffDashboard(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(20, 10))
        ctk.CTkLabel(header, text="Staff Dashboard", font=self.tm.header_font).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Manage your classes and track student progress.",
            font=self.tm.main_font,
            text_color="gray",
        ).pack(anchor="w")

        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=10)

        kpis = [
            ("My Subjects", "4", "📚", self.tm.accent_color),
            ("Total Students", "120", "🎓", self.tm.success_color),
            ("Average Attendance", "85%", "📈", self.tm.warning_color),
            ("Assignments Pending", "3", "📋", self.tm.danger_color),
            ("Messages", "5", "💬", self.tm.info_color),
        ]

        for i, (title, val, icon, color) in enumerate(kpis):
            card = KPICard(kpi_frame, title=title, value=val, icon=icon, color=color)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            kpi_frame.grid_columnconfigure(i, weight=1)

        # Quick Links
        quick_frame = ctk.CTkFrame(self, fg_color="transparent")
        quick_frame.pack(fill="x", pady=(20, 5))
        ctk.CTkLabel(
            quick_frame, text="Quick Actions", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w")

        actions_frame = ctk.CTkFrame(quick_frame, fg_color="transparent")
        actions_frame.pack(fill="x", pady=5)

        actions = [
            ("✍ Take Attendance", "attendance_taker"),
            ("📝 Enter Results", "result_manager"),
            ("🔍 Student Lookup", "student_lookup"),
        ]
        for i, (text, route) in enumerate(actions):
            btn = ctk.CTkButton(
                actions_frame,
                text=text,
                width=180,
                height=38,
                command=lambda r=route: (
                    master.master.navigate(r) if hasattr(master.master, "navigate") else None
                ),
            )
            btn.grid(row=0, column=i, padx=5, pady=5)

        # Charts Area
        charts_frame = ctk.CTkFrame(self, corner_radius=10)
        charts_frame.pack(fill="both", expand=True, pady=(20, 10))
        ctk.CTkLabel(
            charts_frame,
            text="📊 My Class Analytics",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 5))
        ctk.CTkLabel(
            charts_frame,
            text="Attendance trends and performance charts will appear here.",
            text_color="gray",
        ).pack(expand=True)
