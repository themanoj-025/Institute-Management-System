import customtkinter as ctk

from database.models import Student
from services.course_service import CourseService
from services.result_service import ResultService
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


def _calculate_grade(pct):
    if pct >= 90:
        return "A+"
    elif pct >= 80:
        return "A"
    elif pct >= 70:
        return "B+"
    elif pct >= 60:
        return "B"
    elif pct >= 50:
        return "C"
    elif pct >= 40:
        return "D"
    else:
        return "F"


class ResultManager(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.db_session = db_session
        self.result_service = ResultService(db_session)
        self.course_service = CourseService(db_session)
        self._marks_entries = []

        ctk.CTkLabel(self, text="Result Manager", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )
        ctk.CTkLabel(self, text="Enter student marks. Grades are calculated automatically.").pack(
            anchor="w"
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
            width=180,
        )
        self.course_cb.grid(row=0, column=1, padx=10, pady=10)
        if self._course_map:
            self.course_cb.set(list(self._course_map.keys())[0])

        ctk.CTkLabel(filter_frame, text="Exam Type:").grid(
            row=0, column=2, padx=10, pady=10, sticky="w"
        )
        self.exam_cb = ctk.CTkComboBox(
            filter_frame,
            values=["Midterm", "Final", "Quiz", "Assignment", "Practical"],
            width=130,
        )
        self.exam_cb.grid(row=0, column=3, padx=10, pady=10)
        self.exam_cb.set("Midterm")

        ctk.CTkLabel(filter_frame, text="Total Marks:").grid(
            row=0, column=4, padx=10, pady=10, sticky="w"
        )
        self.total_entry = ctk.CTkEntry(filter_frame, placeholder_text="100", width=80)
        self.total_entry.grid(row=0, column=5, padx=10, pady=10)
        self.total_entry.insert(0, "100")

        ctk.CTkButton(
            filter_frame,
            text="🔍 Load Students",
            command=self._load_students,
            width=130,
        ).grid(row=0, column=6, padx=10, pady=10)

        # Marks entry grid
        self.grid_container = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.grid_container.pack(fill="both", expand=True, pady=10, padx=10)

        self._show_placeholder()

        self.save_btn = ctk.CTkButton(
            self,
            text="💾 Save Results",
            height=40,
            fg_color=self.tm.success_color,
            text_color=("black", "white"),
            command=self._save_results,
        )
        self.save_btn.pack(pady=(0, 10))

    def _show_placeholder(self, msg="Filter by course and exam type, then click Load Students."):
        for w in self.grid_container.winfo_children():
            w.destroy()
        frame = ctk.CTkFrame(self.grid_container, fg_color="transparent")
        frame.pack(expand=True, fill="both", pady=40)
        ctk.CTkLabel(frame, text="📝 Marks Entry", font=ctk.CTkFont(size=16, weight="bold")).pack(
            pady=(10, 5)
        )
        ctk.CTkLabel(frame, text=msg, text_color="gray").pack()

    def _load_students(self):
        course_name = self.course_cb.get()
        course_id = self._course_map.get(course_name)
        if not course_id:
            ToastManager.show(self.winfo_toplevel(), "Please select a valid course.", "warning")
            return

        AsyncLoader.run(
            self,
            lambda: self._fetch_students(course_id),
            self._render_grid,
        )

    def _fetch_students(self, course_id):
        students = self.db_session.query(Student).filter(Student.course_id == course_id).all()
        return [
            {
                "id": s.id,
                "name": f"{s.first_name} {s.last_name}",
                "enrollment": s.enrollment_no,
            }
            for s in students
        ]

    def _render_grid(self, students):
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

        # Header
        header = ctk.CTkFrame(self.grid_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(
            header,
            text="Enrollment",
            font=ctk.CTkFont(weight="bold", size=12),
            width=110,
        ).pack(side="left", padx=5)
        ctk.CTkLabel(
            header,
            text="Student Name",
            font=ctk.CTkFont(weight="bold", size=12),
            width=180,
        ).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Marks", font=ctk.CTkFont(weight="bold", size=12), width=80).pack(
            side="left", padx=5
        )
        ctk.CTkLabel(header, text="Grade", font=ctk.CTkFont(weight="bold", size=12), width=60).pack(
            side="left", padx=5
        )

        self._marks_entries = []
        for idx, stu in enumerate(students):
            bg = ("gray95", "gray17") if idx % 2 == 0 else ("gray90", "gray15")
            row = ctk.CTkFrame(self.grid_container, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=stu["enrollment"], width=110, anchor="w").pack(
                side="left", padx=5, pady=4
            )
            ctk.CTkLabel(row, text=stu["name"], width=180, anchor="w").pack(
                side="left", padx=5, pady=4
            )

            marks_var = ctk.StringVar(value="")
            marks_entry = ctk.CTkEntry(row, width=70, textvariable=marks_var)
            marks_entry.pack(side="left", padx=5, pady=4)

            grade_lbl = ctk.CTkLabel(row, text="—", width=60, anchor="w")
            grade_lbl.pack(side="left", padx=5, pady=4)

            # Auto-calculate grade on key release
            def make_callback(mv=marks_var, gl=grade_lbl):
                def callback(*_):
                    try:
                        total = float(self.total_entry.get() or 100)
                        obtained = float(mv.get() or 0)
                        pct = (obtained / total) * 100 if total > 0 else 0
                        gl.configure(text=_calculate_grade(pct))
                    except (ValueError, ZeroDivisionError):
                        gl.configure(text="—")

                return callback

            marks_var.trace_add("write", make_callback())

            self._marks_entries.append(
                {
                    "student_id": stu["id"],
                    "marks_var": marks_var,
                    "subject_id": 1,
                }
            )

    def _save_results(self):
        if not self._marks_entries:
            ToastManager.show(
                self.winfo_toplevel(),
                "No students loaded. Load students first.",
                "warning",
            )
            return

        exam_type = self.exam_cb.get()
        try:
            total_marks = float(self.total_entry.get() or 100)
        except ValueError:
            ToastManager.show(self.winfo_toplevel(), "Total marks must be a number.", "error")
            return

        records = []
        for item in self._marks_entries:
            marks_str = item["marks_var"].get().strip()
            if not marks_str:
                continue
            try:
                marks = float(marks_str)
            except ValueError:
                continue
            pct = (marks / total_marks) * 100 if total_marks > 0 else 0
            records.append(
                {
                    "student_id": item["student_id"],
                    "subject_id": item["subject_id"],
                    "exam_type": exam_type,
                    "marks": marks,
                    "total": total_marks,
                    "grade": _calculate_grade(pct),
                }
            )

        if not records:
            ToastManager.show(
                self.winfo_toplevel(),
                "No marks entered. Enter marks and try again.",
                "warning",
            )
            return

        try:
            self.result_service.bulk_upsert(records, session_id=1)
            ToastManager.show(
                self.winfo_toplevel(),
                f"Results saved for {len(records)} students ✅",
                "success",
            )
        except Exception as e:
            ToastManager.show(self.winfo_toplevel(), f"Failed to save: {e}", "error")
