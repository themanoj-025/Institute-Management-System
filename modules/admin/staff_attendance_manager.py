from calendar import monthrange
from datetime import date, datetime

import customtkinter as ctk
from sqlalchemy.exc import SQLAlchemyError

from database.models import Staff
from services.staff_attendance_service import StaffAttendanceService
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class StaffAttendanceManager(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.db_session = db_session
        self.attendance_service = StaffAttendanceService(db_session)
        self._all_staff = []
        self._filtered_staff = []

        ctk.CTkLabel(self, text="Staff Attendance Management", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )
        ctk.CTkLabel(
            self,
            text="Review staff attendance records, approve exceptions, and calculate payroll days.",
            font=self.tm.main_font,
            text_color="gray",
        ).pack(anchor="w")

        # Filter bar
        filter_frame = ctk.CTkFrame(self, corner_radius=8)
        filter_frame.pack(fill="x", pady=15, padx=10)

        ctk.CTkLabel(filter_frame, text="Department:").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        self.dept_cb = ctk.CTkComboBox(
            filter_frame,
            values=["All", "IT", "CS", "Design", "Math", "Science", "Management"],
            width=150,
        )
        self.dept_cb.grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkLabel(filter_frame, text="Month:").grid(
            row=0, column=2, padx=10, pady=10, sticky="w"
        )
        self.month_cb = ctk.CTkComboBox(
            filter_frame,
            width=150,
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
        )
        self.month_cb.grid(row=0, column=3, padx=10, pady=10)
        self.month_cb.set(date.today().strftime("%B"))

        ctk.CTkLabel(filter_frame, text="Year:").grid(row=0, column=4, padx=10, pady=10, sticky="w")
        self.year_cb = ctk.CTkComboBox(filter_frame, values=["2024", "2025", "2026"], width=100)
        self.year_cb.grid(row=0, column=5, padx=10, pady=10)
        self.year_cb.set(str(date.today().year))

        ctk.CTkButton(
            filter_frame,
            text="📋 Load Report",
            width=120,
            command=self._load_report,
        ).grid(row=0, column=6, padx=10, pady=10)

        # Summary cards
        summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        summary_frame.pack(fill="x", pady=10, padx=10)

        stats = [
            ("Total Staff", "—", "👥", self.tm.accent_color),
            ("Present Today", "—", "✅", self.tm.success_color),
            ("On Leave/Absent", "—", "❌", self.tm.danger_color),
            ("Attendance %", "—", "📊", self.tm.info_color),
        ]
        self._stat_labels = {}
        for i, (title, val, icon, color) in enumerate(stats):
            card = ctk.CTkFrame(summary_frame, corner_radius=8, border_width=1, border_color=color)
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            summary_frame.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(
                card,
                text=f"{icon} {title}",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            ).pack(pady=(8, 0))
            lbl = ctk.CTkLabel(
                card,
                text=val,
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=color,
            )
            lbl.pack(pady=(0, 8))
            self._stat_labels[title] = lbl

        # Details grid
        self.details_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.details_frame.pack(fill="both", expand=True, pady=15, padx=10)

        self._show_placeholder()

        # Auto-load
        self.after(300, self._load_report)

    def _show_placeholder(
        self, msg="Select filters and click Load Report to view staff attendance."
    ) -> None:
        for w in self.details_frame.winfo_children():
            w.destroy()
        frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        frame.pack(expand=True, fill="both", pady=40)
        ctk.CTkLabel(
            frame,
            text="📋 Staff Attendance Details",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(10, 5))
        ctk.CTkLabel(frame, text=msg, text_color="gray").pack()

    def _load_report(self) -> None:
        dept = self.dept_cb.get()
        month_name = self.month_cb.get()
        year_str = self.year_cb.get().strip()

        try:
            month = datetime.strptime(month_name, "%B").month
            year = int(year_str)
        except (ValueError, KeyError):
            ToastManager.show(self.winfo_toplevel(), "Invalid month/year selection.", "warning")
            return

        AsyncLoader.run(
            self,
            lambda: self._fetch_data(dept, month, year),
            lambda data: self._render_report(data, year, month),
        )

    def _fetch_data(self, dept, month, year) -> None:
        query = self.db_session.query(Staff)
        if dept != "All":
            query = query.filter(Staff.department == dept)
        staff_list = query.order_by(Staff.first_name).all()

        result = []
        total_present = 0
        total_absent = 0
        total_staff = len(staff_list)

        for staff in staff_list:
            records = self.attendance_service.get_staff_attendance(staff.id, month, year)
            present = sum(1 for r in records if r["status"] in ("present", "late"))
            absent = sum(1 for r in records if r["status"] == "absent")
            _, days_in_month = monthrange(year, month)
            pct = round((present / days_in_month) * 100, 1) if days_in_month > 0 else 0

            result.append(
                {
                    "id": staff.id,
                    "name": f"{staff.first_name} {staff.last_name}",
                    "department": staff.department or "—",
                    "present": present,
                    "absent": absent,
                    "total_days": days_in_month,
                    "attendance_pct": pct,
                    "records": records,
                }
            )
            total_present += present
            total_absent += absent

        return {
            "staff": result,
            "total": total_staff,
            "total_present": total_present,
            "total_absent": total_absent,
        }

    def _render_report(self, data, year, month) -> None:
        for w in self.details_frame.winfo_children():
            w.destroy()

        staff_data = data["staff"]

        # Update summary stats
        total = data["total"]
        present_today_count = sum(
            1
            for s in staff_data
            if any(
                r["status"] in ("present", "late") and r["date"] == date.today().isoformat()
                for r in s["records"]
            )
        )
        absent_today = total - present_today_count
        avg_pct = (
            round(sum(s["attendance_pct"] for s in staff_data) / len(staff_data), 1)
            if staff_data
            else 0
        )

        self._stat_labels["Total Staff"].configure(text=str(total))
        self._stat_labels["Present Today"].configure(text=str(present_today_count))
        self._stat_labels["On Leave/Absent"].configure(text=str(absent_today))
        self._stat_labels["Attendance %"].configure(text=f"{avg_pct}%")

        if not staff_data:
            frame = ctk.CTkFrame(self.details_frame, fg_color="transparent")
            frame.pack(expand=True, fill="both", pady=40)
            ctk.CTkLabel(
                frame,
                text="📭 No staff found",
                font=ctk.CTkFont(size=14),
            ).pack()
            ctk.CTkLabel(
                frame,
                text="No staff members found for the selected filters.",
                text_color="gray",
            ).pack()
            return

        # Month header
        month_name = date(year, month, 1).strftime("%B %Y")
        ctk.CTkLabel(
            self.details_frame,
            text=f"{month_name} — {total} staff members",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(5, 10))

        # Table header
        header = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        headers = ["Name", "Department", "Present", "Absent", "Days", "%"]
        widths = [180, 120, 70, 70, 60, 60]
        for h, w in zip(headers, widths):
            ctk.CTkLabel(
                header,
                text=h,
                font=ctk.CTkFont(weight="bold", size=11),
                width=w,
                anchor="w",
            ).pack(side="left", padx=5)

        # Staff rows
        for idx, s in enumerate(staff_data):
            bg = ("gray95", "gray17") if idx % 2 == 0 else ("gray90", "gray15")
            row = ctk.CTkFrame(self.details_frame, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)

            pct_color = (
                self.tm.success_color
                if s["attendance_pct"] >= 75
                else (self.tm.warning_color if s["attendance_pct"] >= 50 else self.tm.danger_color)
            )

            cells = [
                (s["name"], 180),
                (s["department"], 120),
                (str(s["present"]), 70),
                (str(s["absent"]), 70),
                (str(s["total_days"]), 60),
                (f"{s['attendance_pct']}%", 60),
            ]
            for i, (val, w) in enumerate(cells):
                ctk.CTkLabel(
                    row,
                    text=val,
                    width=w,
                    anchor="w",
                    font=ctk.CTkFont(size=12),
                    text_color=pct_color if i == 5 else None,
                ).pack(side="left", padx=5, pady=5)

            # Expand button
            expand_btn = ctk.CTkButton(
                row,
                text="🔽",
                width=30,
                height=24,
                fg_color="transparent",
                hover_color=self.tm.accent_color,
                font=ctk.CTkFont(size=10),
                command=lambda sid=s["id"], sn=s["name"]: self._show_staff_detail(sid, sn),
            )
            expand_btn.pack(side="right", padx=5)

    def _show_staff_detail(self, staff_id, staff_name) -> None:
        """Open a dialog showing per-day attendance for a specific staff member."""
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title(f"Attendance — {staff_name}")
        dialog.geometry("550x400")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.winfo_toplevel())
        dialog.focus()

        main = ctk.CTkFrame(dialog, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            main,
            text=f"📋 {staff_name}'s Attendance",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", pady=(0, 10))

        text_area = ctk.CTkTextbox(main, wrap="none", state="disabled")
        text_area.pack(fill="both", expand=True)

        text_area.configure(state="normal")
        text_area.insert("end", f"{'Date':<15}{'Status':<12}{'In':<10}{'Out':<10}\n")
        text_area.insert("end", "-" * 47 + "\n")

        # Fetch and display records for current month/year
        month_name = self.month_cb.get()
        year_str = self.year_cb.get().strip()
        try:
            month = datetime.strptime(month_name, "%B").month
            year = int(year_str)
            records = self.attendance_service.get_staff_attendance(staff_id, month, year)
            for r in records:
                text_area.insert(
                    "end",
                    f"{r['date']:<15}{r['status'].capitalize():<12}"
                    f"{r.get('in_time', '—'):<10}{r.get('out_time', '—'):<10}\n",
                )
        except (SQLAlchemyError, ValueError) as e:
            text_area.insert("end", f"Error loading records: {e}\n")

        text_area.configure(state="disabled")

        ctk.CTkButton(
            dialog,
            text="Close",
            command=dialog.destroy,
            width=100,
            fg_color=self.tm.danger_color,
        ).pack(pady=(10, 5))
