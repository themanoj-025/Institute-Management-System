from collections import defaultdict

import customtkinter as ctk

from database.models import Attendance
from services.attendance_service import AttendanceService
from utils.async_loader import AsyncLoader


class ViewAttendance(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.attendance_service = AttendanceService(db_session)
        self.app_state = app_state
        self.db_session = db_session

        ctk.CTkLabel(self, text="My Attendance", font=self.tm.header_font).pack(pady=20, anchor="w")

        # Stats overview
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)

        cards = [
            ("Total Days", "—", self.tm.accent_color),
            ("Present", "—", self.tm.success_color),
            ("Absent", "—", self.tm.danger_color),
            ("Attendance %", "—", self.tm.info_color),
        ]
        self._stat_labels = {}
        for i, (title, val, color) in enumerate(cards):
            f = ctk.CTkFrame(stats_frame, corner_radius=8, border_width=1, border_color=color)
            f.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=12), text_color="gray").pack(
                pady=(10, 0)
            )
            lbl = ctk.CTkLabel(
                f, text=val, font=ctk.CTkFont(size=22, weight="bold"), text_color=color
            )
            lbl.pack(pady=(0, 10))
            self._stat_labels[title] = lbl

        # Subject-wise breakdown
        self.sub_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.sub_frame.pack(fill="both", expand=True, pady=20)

        ctk.CTkLabel(
            self.sub_frame,
            text="📅 Subject-wise Attendance Breakdown",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 5), padx=10, anchor="w")

        self._sub_content = ctk.CTkFrame(self.sub_frame, fg_color="transparent")
        self._sub_content.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(
            self._sub_content,
            text="Loading attendance records...",
            text_color="gray",
        ).pack(pady=20)

        # Auto-load
        self.after(300, self._load_attendance)

    def _load_attendance(self) -> None:
        student_id = self.app_state.current_user.get("profile_id")
        if not student_id:
            ctk.CTkLabel(
                self._sub_content,
                text="Student profile not found.",
                text_color="gray",
            ).pack(pady=20)
            return

        AsyncLoader.run(
            self,
            lambda: self._fetch_data(student_id),
            self._render_attendance,
        )

    def _fetch_data(self, student_id) -> None:
        records = (
            self.db_session.query(Attendance)
            .filter(Attendance.student_id == student_id)
            .order_by(Attendance.date.desc())
            .all()
        )

        # Group by subject
        by_subject = defaultdict(list)
        for r in records:
            subj_name = r.subject.name if r.subject else f"Subject #{r.subject_id}"
            by_subject[subj_name].append(r)

        # Calculate per-subject stats
        subjects = []
        total_present = 0
        total_absent = 0
        total_late = 0
        total_records = len(records)

        for subj_name, subj_records in sorted(by_subject.items()):
            present = sum(1 for r in subj_records if r.status.value in ("present", "late"))
            absent = sum(1 for r in subj_records if r.status.value == "absent")
            late = sum(1 for r in subj_records if r.status.value == "late")
            excused = sum(1 for r in subj_records if r.status.value == "excused")
            pct = round((present / len(subj_records)) * 100, 1) if subj_records else 0

            subjects.append(
                {
                    "name": subj_name,
                    "present": present,
                    "absent": absent,
                    "late": late,
                    "excused": excused,
                    "total": len(subj_records),
                    "pct": pct,
                }
            )

            total_present += present
            total_absent += absent
            total_late += late

        overall_pct = round((total_present / total_records) * 100, 1) if total_records > 0 else 0

        return {
            "subjects": subjects,
            "total": total_records,
            "present": total_present,
            "absent": total_absent,
            "late": total_late,
            "overall_pct": overall_pct,
        }

    def _render_attendance(self, data) -> None:
        for w in self._sub_content.winfo_children():
            w.destroy()

        if not data or data["total"] == 0:
            self._stat_labels["Total Days"].configure(text="0")
            self._stat_labels["Present"].configure(text="0")
            self._stat_labels["Absent"].configure(text="0")
            self._stat_labels["Attendance %"].configure(text="—")
            ctk.CTkLabel(
                self._sub_content,
                text="No attendance records found for your account.",
                text_color="gray",
            ).pack(pady=20)
            return

        # Update summary stats
        self._stat_labels["Total Days"].configure(text=str(data["total"]))
        self._stat_labels["Present"].configure(
            text=str(data["present"]), text_color=self.tm.success_color
        )
        self._stat_labels["Absent"].configure(
            text=str(data["absent"]), text_color=self.tm.danger_color
        )

        pct = data["overall_pct"]
        pct_color = (
            self.tm.success_color
            if pct >= 75
            else (self.tm.warning_color if pct >= 50 else self.tm.danger_color)
        )
        self._stat_labels["Attendance %"].configure(text=f"{pct}%", text_color=pct_color)

        # Overall attendance bar
        bar_frame = ctk.CTkFrame(
            self._sub_content,
            corner_radius=8,
            border_width=1,
            border_color=self.tm.accent_color,
        )
        bar_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            bar_frame,
            text=f"📊 Overall Attendance: {pct}% — "
            f"{data['present']} Present / {data['absent']} Absent / {data['late']} Late",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=pct_color,
        ).pack(pady=10, padx=15)

        # Subject cards
        for idx, subj in enumerate(data["subjects"]):
            subj_pct = subj["pct"]
            subj_color = (
                self.tm.success_color
                if subj_pct >= 75
                else (self.tm.warning_color if subj_pct >= 50 else self.tm.danger_color)
            )

            card = ctk.CTkFrame(
                self._sub_content,
                corner_radius=8,
                border_width=1,
                border_color=subj_color,
            )
            card.pack(fill="x", pady=5)

            # Subject header row
            header_row = ctk.CTkFrame(card, fg_color="transparent")
            header_row.pack(fill="x", padx=12, pady=(8, 2))
            ctk.CTkLabel(
                header_row,
                text=subj["name"],
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(side="left")

            # Attendance percentage badge
            badge = ctk.CTkLabel(
                header_row,
                text=f"{subj_pct}%",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=subj_color,
            )
            badge.pack(side="right")

            # Stats row
            stats_row = ctk.CTkFrame(card, fg_color="transparent")
            stats_row.pack(fill="x", padx=12, pady=(0, 8))

            stat_items = [
                ("Present", subj["present"], self.tm.success_color),
                ("Absent", subj["absent"], self.tm.danger_color),
                ("Late", subj["late"], self.tm.warning_color),
                ("Total", subj["total"], self.tm.accent_color),
            ]
            for label, val, color in stat_items:
                item = ctk.CTkFrame(stats_row, fg_color="transparent")
                item.pack(side="left", padx=(0, 20))
                ctk.CTkLabel(
                    item,
                    text=label,
                    font=ctk.CTkFont(size=10),
                    text_color="gray",
                ).pack(anchor="center")
                ctk.CTkLabel(
                    item,
                    text=str(val),
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=color,
                ).pack(anchor="center")
