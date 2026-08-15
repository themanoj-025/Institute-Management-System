from datetime import date

import customtkinter as ctk

from database.models import Student
from services.attendance_service import AttendanceService
from services.course_service import CourseService
from services.student_service import StudentService
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class AttendanceTaker(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.attendance_service = AttendanceService(db_session)
        self.course_service = CourseService(db_session)
        self.student_service = StudentService(db_session)
        self.db_session = db_session
        self._students_data = []

        ctk.CTkLabel(self, text="Take Attendance", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        # Filter bar
        filter_frame = ctk.CTkFrame(self, corner_radius=8)
        filter_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(filter_frame, text="Course:").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        courses = self.course_service.get_all_courses()
        self._course_map = {f"{c['name']} ({c['code']})": c["id"] for c in courses}
        self.course_cb = ctk.CTkComboBox(
            filter_frame,
            values=list(self._course_map.keys()) or ["No courses"],
            width=200,
        )
        self.course_cb.grid(row=0, column=1, padx=10, pady=10)
        if self._course_map:
            self.course_cb.set(list(self._course_map.keys())[0])

        ctk.CTkLabel(filter_frame, text="Date:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.date_entry = ctk.CTkEntry(filter_frame, placeholder_text="YYYY-MM-DD", width=120)
        self.date_entry.grid(row=0, column=3, padx=10, pady=10)
        self.date_entry.insert(0, date.today().isoformat())

        ctk.CTkButton(
            filter_frame,
            text="🔍 Load Students",
            command=self._load_students,
            width=130,
        ).grid(row=0, column=4, padx=10, pady=10)

        # Attendance grid
        self.grid_container = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.grid_container.pack(fill="both", expand=True, pady=10, padx=10)

        self._show_placeholder()

        # Save button
        self.save_btn = ctk.CTkButton(
            self,
            text="💾 Save Attendance",
            height=40,
            fg_color=self.tm.success_color,
            text_color=("black", "white"),
            command=self._save_attendance,
        )
        self.save_btn.pack(pady=(0, 10))

    def _show_placeholder(self, msg="Select course and date above, then click Load Students."):
        for w in self.grid_container.winfo_children():
            w.destroy()
        frame = ctk.CTkFrame(self.grid_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", pady=40)
        ctk.CTkLabel(
            frame,
            text="📋 Student Attendance",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(10, 5))
        ctk.CTkLabel(frame, text=msg, text_color="gray").pack()

    def _load_students(self):
        course_name = self.course_cb.get()
        course_id = self._course_map.get(course_name)
        if not course_id:
            ToastManager.show(self.winfo_toplevel(), "Please select a valid course.", "warning")
            return

        date_str = self.date_entry.get().strip()
        try:
            att_date = date.fromisoformat(date_str)
        except ValueError:
            ToastManager.show(self.winfo_toplevel(), "Invalid date. Use YYYY-MM-DD.", "error")
            return

        AsyncLoader.run(
            self,
            lambda: self._fetch_students(course_id, att_date),
            lambda data: self._render_grid(data, att_date),
        )

    def _fetch_students(self, course_id, att_date):
        students = self.db_session.query(Student).filter(Student.course_id == course_id).all()
        existing = self.attendance_service.get_by_date_subject(att_date, 0)
        # We don't filter by subject here; show all students in the course
        result = []
        for s in students:
            result.append(
                {
                    "id": s.id,
                    "name": f"{s.first_name} {s.last_name}",
                    "enrollment": s.enrollment_no,
                    "status": existing.get(s.id, None),
                }
            )
        return result

    def _render_grid(self, students, att_date):
        for w in self.grid_container.winfo_children():
            w.destroy()

        if not students:
            frame = ctk.CTkFrame(self.grid_container, fg_color="transparent")
            frame.pack(expand=True, fill="both", pady=40)
            ctk.CTkLabel(frame, text="📭 No students found", font=ctk.CTkFont(size=14)).pack()
            ctk.CTkLabel(
                frame,
                text="No students are enrolled in this course.",
                text_color="gray",
            ).pack()
            return

        # Header row
        header = ctk.CTkFrame(self.grid_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(
            header,
            text="Enrollment",
            font=ctk.CTkFont(weight="bold", size=12),
            width=100,
        ).pack(side="left", padx=5)
        ctk.CTkLabel(
            header,
            text="Student Name",
            font=ctk.CTkFont(weight="bold", size=12),
            width=200,
        ).pack(side="left", padx=5)
        ctk.CTkLabel(
            header, text="Status", font=ctk.CTkFont(weight="bold", size=12), width=150
        ).pack(side="left", padx=5)

        self._students_data = []
        for idx, stu in enumerate(students):
            bg = ("gray95", "gray17") if idx % 2 == 0 else ("gray90", "gray15")
            row = ctk.CTkFrame(self.grid_container, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=stu["enrollment"], width=100, anchor="w").pack(
                side="left", padx=5, pady=4
            )
            ctk.CTkLabel(row, text=stu["name"], width=200, anchor="w").pack(
                side="left", padx=5, pady=4
            )

            status_var = ctk.StringVar(value=stu["status"].value if stu["status"] else "present")
            cb = ctk.CTkComboBox(
                row,
                values=["present", "absent", "late", "excused"],
                variable=status_var,
                width=140,
                state="readonly",
            )
            cb.pack(side="left", padx=5, pady=4)

            self._students_data.append(
                {
                    "student_id": stu["id"],
                    "status_var": status_var,
                }
            )

    def _save_attendance(self):
        if not self._students_data:
            ToastManager.show(
                self.winfo_toplevel(),
                "No students loaded. Load students first.",
                "warning",
            )
            return

        date_str = self.date_entry.get().strip()
        records = []
        for item in self._students_data:
            records.append(
                {
                    "student_id": item["student_id"],
                    "subject_id": 1,
                    "date": date_str,
                    "status": item["status_var"].get(),
                }
            )

        try:
            staff_id = self.app_state.current_user.get("profile_id", 1)
            self.attendance_service.bulk_upsert(records, staff_id)
            ToastManager.show(
                self.winfo_toplevel(),
                f"Attendance saved for {len(records)} students ✅",
                "success",
            )
        except Exception as e:
            ToastManager.show(self.winfo_toplevel(), f"Failed to save: {e}", "error")
