from datetime import datetime

import customtkinter as ctk

from database.models import Session as AcadSession
from services.course_service import CourseService
from services.student_service import StudentService
from ui.data_table import DataTable
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class ManageStudents(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.db_session = db_session
        self.student_service = StudentService(db_session)
        self.course_service = CourseService(db_session)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=20)

        ctk.CTkLabel(header_frame, text="Manage Students", font=self.tm.header_font).pack(
            side="left"
        )
        ctk.CTkButton(
            header_frame,
            text="+ Add Student",
            command=self._add_student,
            fg_color=self.tm.success_color,
            text_color=("black", "white"),
            hover_color=self.tm.info_color,
        ).pack(side="right")

        self.table = DataTable(
            self, columns=["ID", "Enrollment No", "Name", "Course", "Session"], data=[]
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            res = self.student_service.get_all_students(limit=25)
            return [
                [
                    s["id"],
                    s["enrollment_no"],
                    s["full_name"],
                    s.get("course", "N/A"),
                    s.get("session", "N/A"),
                ]
                for s in res.get("students", [])
            ]

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)

    def _add_student(self) -> None:
        """Open a dialog to add a new student."""
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Add New Student")
        dialog.geometry("520x620")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.focus()
        dialog.attributes("-topmost", True)

        # Center on parent
        dialog.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() - 520) // 2
            y = self.winfo_rooty() + (self.winfo_height() - 620) // 2
            dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(frame, text="Add New Student", font=ctk.CTkFont(size=18, weight="bold")).pack(
            pady=(0, 15)
        )

        # ── First Name ──
        ctk.CTkLabel(frame, text="First Name *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        first_name_entry = ctk.CTkEntry(frame, placeholder_text="First name", width=460)
        first_name_entry.pack(pady=(3, 6))

        # ── Last Name ──
        ctk.CTkLabel(frame, text="Last Name *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        last_name_entry = ctk.CTkEntry(frame, placeholder_text="Last name", width=460)
        last_name_entry.pack(pady=(3, 6))

        # ── Email ──
        ctk.CTkLabel(frame, text="Email *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        email_entry = ctk.CTkEntry(frame, placeholder_text="student@example.com", width=460)
        email_entry.pack(pady=(3, 6))

        # ── Phone ──
        ctk.CTkLabel(frame, text="Phone *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        phone_entry = ctk.CTkEntry(frame, placeholder_text="10-digit mobile number", width=460)
        phone_entry.pack(pady=(3, 6))

        # ── DOB ──
        ctk.CTkLabel(
            frame,
            text="Date of Birth (YYYY-MM-DD) *",
            anchor="w",
            font=self.tm.main_font,
        ).pack(fill="x", pady=(3, 0))
        dob_entry = ctk.CTkEntry(frame, placeholder_text="e.g. 2000-01-15", width=460)
        dob_entry.pack(pady=(3, 6))

        # ── Gender ──
        ctk.CTkLabel(frame, text="Gender *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        gender_cb = ctk.CTkComboBox(frame, values=["Male", "Female", "Other"], width=460)
        gender_cb.pack(pady=(3, 6))
        gender_cb.set("Male")

        # ── Course ──
        ctk.CTkLabel(frame, text="Course *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        courses = self.course_service.get_all_courses()
        course_options = {f"{c['name']} ({c['code']})": c["id"] for c in courses}
        course_names = list(course_options.keys())
        course_cb = ctk.CTkComboBox(
            frame,
            values=course_names if course_names else ["No courses available"],
            width=460,
        )
        course_cb.pack(pady=(3, 6))
        if course_names:
            course_cb.set(course_names[0])

        # ── Session ──
        ctk.CTkLabel(frame, text="Session *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        sessions = self.db_session.query(AcadSession).filter(AcadSession.is_active == True).all()
        session_options = {s.name: s.id for s in sessions}
        session_names = list(session_options.keys())
        session_cb = ctk.CTkComboBox(
            frame,
            values=session_names if session_names else ["No active sessions"],
            width=460,
        )
        session_cb.pack(pady=(3, 10))
        if session_names:
            session_cb.set(session_names[0])

        # ── Error label ──
        error_lbl = ctk.CTkLabel(
            frame, text="", text_color=self.tm.danger_color, font=self.tm.small_font
        )
        error_lbl.pack(pady=(0, 5))

        # ── Buttons ──
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(5, 0))

        def submit() -> None:
            first_name = first_name_entry.get().strip()
            last_name = last_name_entry.get().strip()
            email = email_entry.get().strip()
            phone = phone_entry.get().strip()
            dob_str = dob_entry.get().strip()
            gender = gender_cb.get()
            course_name = course_cb.get()
            session_name = session_cb.get()

            # Validate
            if not first_name:
                error_lbl.configure(text="First name is required.")
                return
            if not last_name:
                error_lbl.configure(text="Last name is required.")
                return
            if not email or "@" not in email:
                error_lbl.configure(text="A valid email address is required.")
                return
            if not phone or len(phone) < 10:
                error_lbl.configure(text="Phone number must be at least 10 digits.")
                return
            try:
                parsed_dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                error_lbl.configure(text="DOB must be in YYYY-MM-DD format.")
                return
            if course_name not in course_options:
                error_lbl.configure(text="Please select a valid course.")
                return
            if session_name not in session_options:
                error_lbl.configure(text="Please select a valid session.")
                return

            course_id = course_options[course_name]
            session_id = session_options[session_name]
            username = email.split("@")[0]

            try:
                self.student_service.create_student(
                    {
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "phone": phone,
                        "dob": parsed_dob,
                        "gender": gender,
                        "course_id": course_id,
                        "session_id": session_id,
                        "address": "",
                    }
                )
                dialog.destroy()
                ToastManager.show(
                    self.winfo_toplevel(),
                    f"Student {first_name} {last_name} enrolled successfully ✅",
                    "success",
                )
                self._load_data()
            except Exception as e:
                error_lbl.configure(text=f"Failed to create student: {e}")

        ctk.CTkButton(
            btn_frame,
            text="✅ Enroll Student",
            command=submit,
            fg_color=self.tm.success_color,
            text_color=("black", "white"),
            width=160,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color="gray",
            width=100,
        ).pack(side="left", padx=6)
