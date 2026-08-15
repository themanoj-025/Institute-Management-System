from calendar import monthrange
from datetime import date, datetime

import customtkinter as ctk

from services.staff_attendance_service import StaffAttendanceService
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class MyAttendance(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.attendance_service = StaffAttendanceService(db_session)

        ctk.CTkLabel(self, text="My Attendance", font=self.tm.header_font).pack(pady=20, anchor="w")

        # Monthly filter
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(filter_frame, text="Month:").pack(side="left", padx=(0, 10))
        self.month_cb = ctk.CTkComboBox(
            filter_frame,
            values=[
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ],
            width=150,
        )
        self.month_cb.pack(side="left", padx=5)
        self.month_cb.set(date.today().strftime("%B"))

        ctk.CTkLabel(filter_frame, text="Year:").pack(side="left", padx=(15, 5))
        self.year_cb = ctk.CTkComboBox(filter_frame, values=["2024", "2025", "2026"], width=100)
        self.year_cb.pack(side="left", padx=5)
        self.year_cb.set(str(date.today().year))

        ctk.CTkButton(
            filter_frame,
            text="🔍 Load",
            width=100,
            command=self._load_attendance,
        ).pack(side="left", padx=15)

        # Stats bar
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)

        stats = [
            ("Present", "—", self.tm.success_color),
            ("Absent", "—", self.tm.danger_color),
            ("Late", "—", self.tm.warning_color),
            ("Excused", "—", self.tm.info_color),
        ]
        self._stat_labels = {}
        for i, (title, val, color) in enumerate(stats):
            f = ctk.CTkFrame(stats_frame, corner_radius=6, border_width=1, border_color=color)
            f.pack(side="left", padx=10, fill="x", expand=True)
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=11), text_color="gray").pack(
                pady=(8, 0)
            )
            lbl = ctk.CTkLabel(
                f, text=val, font=ctk.CTkFont(size=20, weight="bold"), text_color=color
            )
            lbl.pack(pady=(0, 8))
            self._stat_labels[title.lower()] = lbl

        # Calendar grid
        self.cal_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.cal_frame.pack(fill="both", expand=True, pady=20)
        self._show_placeholder()

        # Auto-load
        self.after(300, self._load_attendance)

    def _show_placeholder(self):
        for w in self.cal_frame.winfo_children():
            w.destroy()
        frame = ctk.CTkFrame(self.cal_frame, fg_color="transparent")
        frame.pack(expand=True, fill="both", pady=40)
        ctk.CTkLabel(
            frame,
            text="📅 Monthly Attendance Calendar",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(10, 5))
        ctk.CTkLabel(
            frame,
            text="Loading your attendance records...",
            text_color="gray",
        ).pack(expand=True)

    def _load_attendance(self):
        month_name = self.month_cb.get()
        year_str = self.year_cb.get().strip()
        try:
            month = datetime.strptime(month_name, "%B").month
            year = int(year_str)
        except (ValueError, KeyError):
            ToastManager.show(self.winfo_toplevel(), "Invalid month/year selection.", "warning")
            return

        staff_id = self.app_state.current_user.get("profile_id")
        if not staff_id:
            ToastManager.show(self.winfo_toplevel(), "Staff profile not found.", "error")
            return

        AsyncLoader.run(
            self,
            lambda: self.attendance_service.get_staff_attendance(staff_id, month, year),
            lambda records: self._render_calendar(records, year, month),
        )

    def _render_calendar(self, records, year, month):
        for w in self.cal_frame.winfo_children():
            w.destroy()

        # Build lookup: date -> status
        record_map = {}
        present = absent = late = excused = 0
        for r in records:
            record_map[r["date"]] = r["status"]
            if r["status"] == "present":
                present += 1
            elif r["status"] == "absent":
                absent += 1
            elif r["status"] == "late":
                late += 1
            elif r["status"] == "excused":
                excused += 1

        # Update stats
        total = present + absent + late + excused
        self._stat_labels["present"].configure(text=str(present) if total > 0 else "—")
        self._stat_labels["absent"].configure(text=str(absent) if total > 0 else "—")
        self._stat_labels["late"].configure(text=str(late) if total > 0 else "—")
        self._stat_labels["excused"].configure(text=str(excused) if total > 0 else "—")

        # Month/Year header
        month_name = date(year, month, 1).strftime("%B %Y")
        ctk.CTkLabel(
            self.cal_frame,
            text=f"📅 {month_name}",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(10, 10))

        _, days_in_month = monthrange(year, month)
        first_weekday = date(year, month, 1).weekday()  # Monday=0

        # Day-of-week headers
        day_header = ctk.CTkFrame(self.cal_frame, fg_color="transparent")
        day_header.pack(fill="x", pady=(0, 5))
        for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            ctk.CTkLabel(
                day_header,
                text=d,
                font=ctk.CTkFont(weight="bold", size=11),
                width=80,
                anchor="center",
            ).grid(row=0, column=i, padx=2, pady=2)

        # Calendar grid
        cal_grid = ctk.CTkFrame(self.cal_frame, fg_color="transparent")
        cal_grid.pack(fill="x")

        STATUS_COLORS = {
            "present": ("#a6e3a1", "#2e7d32"),
            "absent": ("#f38ba8", "#c62828"),
            "late": ("#fab387", "#e65100"),
            "excused": ("#89b4fa", "#1565c0"),
        }

        # Empty cells before first day
        row = 0
        for _ in range(first_weekday):
            ctk.CTkLabel(cal_grid, text="", width=80, height=50).grid(
                row=row, column=_, padx=2, pady=2
            )

        # Day cells
        col = first_weekday
        for day_num in range(1, days_in_month + 1):
            date_iso = date(year, month, day_num).isoformat()
            status = record_map.get(date_iso)

            if status and status in STATUS_COLORS:
                bg_color, text_color = STATUS_COLORS[status]
                cell = ctk.CTkFrame(cal_grid, fg_color=bg_color, corner_radius=6)
            else:
                bg_color = ("gray90", "gray20")
                text_color = ("black", "white")
                cell = ctk.CTkFrame(cal_grid, fg_color=bg_color, corner_radius=6)

            cell.grid(row=row + 1, column=col, padx=2, pady=2, sticky="nsew")
            cal_grid.grid_columnconfigure(col, weight=1)

            inner = ctk.CTkFrame(cell, fg_color="transparent")
            inner.pack(expand=True, fill="both", pady=4)

            ctk.CTkLabel(
                inner,
                text=str(day_num),
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=text_color,
            ).pack()

            if status:
                s_lbl = ctk.CTkLabel(
                    inner,
                    text=status.capitalize(),
                    font=ctk.CTkFont(size=9),
                    text_color=text_color,
                )
                s_lbl.pack()

            col += 1
            if col > 6:  # Sunday
                col = 0
                row += 1
