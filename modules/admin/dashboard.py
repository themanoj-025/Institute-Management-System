import customtkinter as ctk

from ui.components import KPICard


class AdminDashboard(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm

        # Header with greeting
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(20, 10))
        ctk.CTkLabel(header, text="Admin Dashboard", font=self.tm.header_font).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Welcome back! Here's your institute overview.",
            font=self.tm.main_font,
            text_color="gray",
        ).pack(anchor="w")

        kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=10)

        # 6 KPI cards
        kpis = [
            ("Total Students", "5,000", "🎓", self.tm.accent_color),
            ("Total Staff", "50", "👨‍🏫", self.tm.success_color),
            ("Active Courses", "12", "📚", self.tm.warning_color),
            ("Total Revenue", "₹1.5Cr", "💰", self.tm.danger_color),
            ("Pending Leaves", "15", "📝", self.tm.info_color),
            ("Unread Enquiries", "8", "📬", "gray"),
        ]

        for i, (title, val, icon, color) in enumerate(kpis):
            row = i // 3
            col = i % 3
            card = KPICard(kpi_frame, title=title, value=val, icon=icon, color=color)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            kpi_frame.grid_columnconfigure(col, weight=1)
            kpi_frame.grid_rowconfigure(row, weight=1)

        # Quick Actions
        quick_frame = ctk.CTkFrame(self, fg_color="transparent")
        quick_frame.pack(fill="x", pady=(20, 5))
        ctk.CTkLabel(
            quick_frame, text="Quick Actions", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w")

        actions_frame = ctk.CTkFrame(quick_frame, fg_color="transparent")
        actions_frame.pack(fill="x", pady=5)

        actions = [
            ("➕ Add Student", "manage_students"),
            ("📋 Take Attendance", "staff_attendance"),
            ("📊 View Reports", "reports_center"),
            ("📢 Publish Notice", "notice_board"),
        ]
        for i, (text, route) in enumerate(actions):
            btn = ctk.CTkButton(
                actions_frame,
                text=text,
                width=160,
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
            text="📊 Charts & Analytics",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 5))
        ctk.CTkLabel(
            charts_frame,
            text="Visual analytics will render here — attendance trends, revenue charts, and more.",
            text_color="gray",
        ).pack(expand=True)
