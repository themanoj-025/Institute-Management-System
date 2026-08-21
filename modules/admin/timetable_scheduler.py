import customtkinter as ctk

from services.course_service import CourseService
from services.timetable_service import TimetableService
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class TimetableScheduler(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.timetable_service = TimetableService(db_session)
        self.course_service = CourseService(db_session)
        self._current_course_id = None
        self._course_map = {}  # display_name -> id

        self._build_ui()
        self._load_courses()

    def _build_ui(self) -> None:
        # ── Header ──
        ctk.CTkLabel(self, text="Timetable Scheduler", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )
        ctk.CTkLabel(
            self,
            text="Manage course schedules, detect clashes, and auto-generate timetables.",
            font=self.tm.main_font,
            text_color="gray",
        ).pack(anchor="w")

        # ── Top bar with course selector and controls ──
        top_bar = ctk.CTkFrame(self, corner_radius=8)
        top_bar.pack(fill="x", pady=15, padx=10)

        ctk.CTkLabel(top_bar, text="Course:").pack(side="left", padx=(15, 5))
        self.course_cb = ctk.CTkComboBox(top_bar, values=["Select a course..."], width=220)
        self.course_cb.pack(side="left", padx=5)
        self.course_cb.set("Select a course...")

        ctk.CTkButton(
            top_bar,
            text="📋 Load Timetable",
            width=140,
            height=36,
            fg_color=self.tm.accent_color,
            command=self._load_timetable,
        ).pack(side="left", padx=5)

        self.auto_gen_btn = ctk.CTkButton(
            top_bar,
            text="🔄 Auto-Generate",
            width=160,
            height=36,
            fg_color=self.tm.success_color,
            text_color=("black", "white"),
            command=self._auto_generate,
        )
        self.auto_gen_btn.pack(side="right", padx=10)

        # ── Timetable grid ──
        self.grid_scroll = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.grid_scroll.pack(fill="both", expand=True, pady=10)

        self._build_empty_grid()

    def _build_empty_grid(self) -> None:
        """Show the empty weekday grid with 'No classes scheduled'."""
        for widget in self.grid_scroll.winfo_children():
            widget.destroy()

        for i, day in enumerate(WEEKDAYS):
            day_frame = ctk.CTkFrame(self.grid_scroll, fg_color="transparent")
            day_frame.pack(fill="x", padx=10, pady=3)
            bg = ("gray95", "gray17") if i % 2 == 0 else ("gray90", "gray15")

            day_lbl = ctk.CTkLabel(
                day_frame,
                text=f"{day}:",
                font=ctk.CTkFont(weight="bold", size=13),
                width=110,
                anchor="w",
                fg_color=bg,
                corner_radius=4,
            )
            day_lbl.pack(side="left", padx=(5, 10), pady=4, fill="x", expand=True)

            ctk.CTkLabel(
                day_frame,
                text="No classes scheduled",
                text_color="gray",
                fg_color=bg,
                corner_radius=4,
            ).pack(side="left", padx=5, pady=4, fill="x", expand=True)

    def _populate_grid(self, entries) -> None:
        """Populate the grid with actual timetable entries, grouped by day."""
        for widget in self.grid_scroll.winfo_children():
            widget.destroy()

        # Group entries by day
        day_entries = {day: [] for day in WEEKDAYS}
        for e in entries:
            day = e.get("day_of_week", "")
            if day in day_entries:
                day_entries[day].append(e)

        has_any = any(len(v) > 0 for v in day_entries.values())

        for i, day in enumerate(WEEKDAYS):
            day_frame = ctk.CTkFrame(self.grid_scroll, fg_color="transparent")
            day_frame.pack(fill="x", padx=10, pady=3)
            bg = ("gray95", "gray17") if i % 2 == 0 else ("gray90", "gray15")

            day_lbl = ctk.CTkLabel(
                day_frame,
                text=f"{day}:",
                font=ctk.CTkFont(weight="bold", size=13),
                width=110,
                anchor="w",
                fg_color=bg,
                corner_radius=4,
            )
            day_lbl.pack(side="left", padx=(5, 10), pady=4)

            entries_for_day = day_entries.get(day, [])
            if not entries_for_day:
                ctk.CTkLabel(
                    day_frame,
                    text="— No classes —",
                    text_color="gray",
                    fg_color=bg,
                    corner_radius=4,
                ).pack(side="left", padx=5, pady=4, fill="x", expand=True)
            else:
                # Show subject + time + staff + room for each entry
                entry_texts = []
                for e in entries_for_day:
                    subject = e.get("subject_name", "N/A")
                    staff = e.get("staff_name", "Unassigned")
                    start = e.get("start_time", "")
                    end = e.get("end_time", "")
                    room = e.get("room_no", "TBD")
                    entry_texts.append(f"{subject} ({start}-{end}) — {staff} — {room}")
                text = " | ".join(entry_texts)
                ctk.CTkLabel(
                    day_frame,
                    text=text,
                    anchor="w",
                    fg_color=bg,
                    corner_radius=4,
                    font=ctk.CTkFont(size=12),
                ).pack(side="left", padx=5, pady=4, fill="x", expand=True)

        if not has_any:
            # Show a helpful message
            info_frame = ctk.CTkFrame(self.grid_scroll, fg_color="transparent")
            info_frame.pack(fill="both", expand=True, pady=30)
            ctk.CTkLabel(
                info_frame,
                text="📅 No timetable entries for this course yet.",
                font=ctk.CTkFont(size=14),
                text_color="gray",
            ).pack()
            ctk.CTkLabel(
                info_frame,
                text="Click 'Auto-Generate' to create a schedule automatically.",
                font=ctk.CTkFont(size=12),
                text_color="gray",
            ).pack(pady=(5, 0))

    def _load_courses(self) -> None:
        """Load courses into the dropdown."""

        def fetch() -> None:
            return self.course_service.get_all_courses()

        def on_success(courses) -> None:
            self._course_map = {f"{c['name']} ({c['code']})": c["id"] for c in courses}
            names = list(self._course_map.keys())
            if names:
                self.course_cb.configure(values=names)
                self.course_cb.set(names[0])
                self._current_course_id = self._course_map[names[0]]
                self._load_timetable()

        AsyncLoader.run(self, fetch, on_success)

    def _load_timetable(self) -> None:
        """Load and display the timetable for the selected course."""
        selected = self.course_cb.get()
        course_id = self._course_map.get(selected)
        if not course_id:
            self._build_empty_grid()
            return

        self._current_course_id = course_id

        def fetch() -> None:
            return self.timetable_service.get_timetable_for_course(course_id)

        def on_success(entries) -> None:
            self._populate_grid(entries)

        AsyncLoader.run(self, fetch, on_success)

    def _auto_generate(self) -> None:
        """Auto-generate a timetable for the selected course."""
        selected = self.course_cb.get()
        course_id = self._course_map.get(selected)

        if not course_id:
            ToastManager.show(self.winfo_toplevel(), "Please select a course first.", "warning")
            return

        def fetch() -> None:
            return self.timetable_service.auto_generate(course_id)

        def on_success(result) -> None:
            status = result.get("status", "error")
            message = result.get("message", "Unknown result")
            if status == "created":
                ToastManager.show(self.winfo_toplevel(), f"✅ {message}", "success")
                self._populate_grid(result.get("entries", []))
            elif status == "skipped":
                ToastManager.show(self.winfo_toplevel(), f"⚠️ {message}", "warning")
            else:
                ToastManager.show(self.winfo_toplevel(), f"❌ {message}", "error")

        AsyncLoader.run(self, fetch, on_success)
