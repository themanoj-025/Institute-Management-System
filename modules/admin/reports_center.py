import os

import customtkinter as ctk
from datetime import timedelta

from sqlalchemy import case, func

from services.export_service import ExportService
from ui.toast import ToastManager

from database.models import (
    Attendance,
    Course,
    Fee,
    Placement,
    Result,
    Staff,
    StaffAttendance,
    Student,
    Subject,
)
from utils.time import utc_now


class ReportsCenter(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.db_session = db_session
        self.app_state = app_state
        self.export_svc = ExportService()

        ctk.CTkLabel(self, text="Reports Center", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        reports = [
            ("Attendance Report (PDF)", self._export_attendance),
            ("Student Marks (Excel)", self._export_marks),
            ("Fee Collection (Excel)", self._export_fees),
            ("At-Risk Students (PDF)", self._export_at_risk),
            ("Topper List (PDF)", self._export_toppers),
            ("Staff Attendance (Excel)", self._export_staff_attendance),
            ("Placement Summary (PDF)", self._export_placements),
            ("Course Enrollment (Excel)", self._export_enrollment),
        ]

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", pady=20)

        for i, (text, command) in enumerate(reports):
            row = i // 4
            col = i % 4
            btn = ctk.CTkButton(
                grid,
                text=text,
                width=200,
                height=80,
                fg_color=self.tm.accent_color,
                command=command,
            )
            btn.grid(row=row, column=col, padx=10, pady=10)

    # ── Helper ─────────────────────────────────────────────────────

    def _export_result(self, filename: str, title: str, headers, rows, fmt: str = "pdf"):
        """Run export and show a toast with the result."""
        try:
            if fmt == "pdf":
                result = self.export_svc.to_pdf(filename, title, headers, rows, landscape=True)
            elif fmt == "xlsx":
                result = self.export_svc.to_excel(filename, headers, rows)
            else:
                result = self.export_svc.to_csv(filename, headers, rows)

            ToastManager.show(
                self.winfo_toplevel(),
                f"{title} saved → {os.path.basename(result.path)}",
                "success",
            )
        except Exception as exc:
            ToastManager.show(self.winfo_toplevel(), f"{title} failed: {exc}", "error")

    # ── 1. Attendance Report (PDF) ─────────────────────────────────

    def _export_attendance(self):
        records = (
            self.db_session.query(
                Student.enrollment_no,
                Student.first_name,
                Student.last_name,
                Subject.name.label("subject"),
                Attendance.date,
                Attendance.status,
            )
            .select_from(Attendance)
            .join(Student, Attendance.student_id == Student.id)
            .join(Subject, Attendance.subject_id == Subject.id)
            .order_by(Attendance.date.desc())
            .limit(5000)
            .all()
        )
        headers = ["Enrollment", "First Name", "Last Name", "Subject", "Date", "Status"]
        rows = [
            [
                r.enrollment_no,
                r.first_name,
                r.last_name,
                r.subject,
                str(r.date),
                r.status.value,
            ]
            for r in records
        ]
        self._export_result("attendance_report.pdf", "Attendance Report", headers, rows, "pdf")

    # ── 2. Student Marks (Excel) ───────────────────────────────────

    def _export_marks(self):
        records = (
            self.db_session.query(
                Student.enrollment_no,
                Student.first_name,
                Student.last_name,
                Subject.name.label("subject"),
                Result.exam_type,
                Result.marks_obtained,
                Result.total_marks,
                Result.grade,
            )
            .select_from(Result)
            .join(Student, Result.student_id == Student.id)
            .join(Subject, Result.subject_id == Subject.id)
            .filter(Result.is_deleted == False)
            .order_by(Student.enrollment_no, Subject.name)
            .limit(5000)
            .all()
        )
        headers = [
            "Enrollment",
            "First Name",
            "Last Name",
            "Subject",
            "Exam Type",
            "Obtained",
            "Total",
            "Grade",
        ]
        rows = [
            [
                r.enrollment_no,
                r.first_name,
                r.last_name,
                r.subject,
                r.exam_type,
                r.marks_obtained,
                r.total_marks,
                r.grade or "-",
            ]
            for r in records
        ]
        self._export_result("student_marks.xlsx", "Student Marks", headers, rows, "xlsx")

    # ── 3. Fee Collection (Excel) ──────────────────────────────────

    def _export_fees(self):
        records = (
            self.db_session.query(
                Student.enrollment_no,
                Student.first_name,
                Student.last_name,
                Fee.total_amount,
                Fee.paid_amount,
                Fee.status,
                Fee.due_date,
                Fee.scholarship_amount,
                Fee.fine_amount,
            )
            .select_from(Fee)
            .join(Student, Fee.student_id == Student.id)
            .filter(Fee.is_deleted == False)
            .order_by(Student.enrollment_no)
            .all()
        )
        headers = [
            "Enrollment",
            "First Name",
            "Last Name",
            "Total Fee",
            "Paid",
            "Balance",
            "Status",
            "Due Date",
            "Scholarship",
            "Fine",
        ]
        rows = []
        for r in records:
            balance = round(
                r.total_amount - r.paid_amount - (r.scholarship_amount or 0) + (r.fine_amount or 0),
                2,
            )
            rows.append(
                [
                    r.enrollment_no,
                    r.first_name,
                    r.last_name,
                    r.total_amount,
                    r.paid_amount,
                    balance,
                    r.status.value if r.status else "unpaid",
                    str(r.due_date) if r.due_date else "-",
                    r.scholarship_amount or 0,
                    r.fine_amount or 0,
                ]
            )
        self._export_result("fee_collection.xlsx", "Fee Collection", headers, rows, "xlsx")

    # ── 4. At-Risk Students (PDF) ──────────────────────────────────

    def _export_at_risk(self):
        """Export student-level KPIs that feed into risk scoring:
        attendance %, average marks, fee status, leave counts."""
        now = utc_now().date()
        cutoff = now - timedelta(days=365)  # ~1 year of history

        # Attendance rate per student over the past ~year
        att_subq = (
            self.db_session.query(
                Attendance.student_id,
                (
                    func.sum(
                        case(
                            (Attendance.status == "present", 1),
                            (Attendance.status == "late", 1),
                            else_=0,
                        )
                    )
                    * 1.0
                    / func.nullif(func.count(Attendance.id), 0)
                ).label("att_pct"),
            )
            .filter(Attendance.date >= cutoff)
            .group_by(Attendance.student_id)
            .subquery()
        )

        # Average marks per student
        marks_subq = (
            self.db_session.query(
                Result.student_id,
                func.avg(Result.marks_obtained * 1.0 / func.nullif(Result.total_marks, 0)).label(
                    "avg_marks_pct"
                ),
            )
            .filter(Result.is_deleted == False)
            .group_by(Result.student_id)
            .subquery()
        )

        students = (
            self.db_session.query(
                Student.enrollment_no,
                Student.first_name,
                Student.last_name,
                Course.name.label("course"),
                att_subq.c.att_pct,
                marks_subq.c.avg_marks_pct,
            )
            .outerjoin(att_subq, Student.id == att_subq.c.student_id)
            .outerjoin(marks_subq, Student.id == marks_subq.c.student_id)
            .outerjoin(Course, Student.course_id == Course.id)
            .order_by(
                att_subq.c.att_pct.asc().nullslast(),
                marks_subq.c.avg_marks_pct.asc().nullslast(),
            )
            .limit(500)
            .all()
        )

        headers = ["Enrollment", "Name", "Course", "Attend. %", "Avg Marks %"]
        rows = [
            [
                r.enrollment_no,
                f"{r.first_name} {r.last_name}",
                r.course or "-",
                f"{round(r.att_pct * 100, 1)}%" if r.att_pct else "N/A",
                f"{round(r.avg_marks_pct * 100, 1)}%" if r.avg_marks_pct else "N/A",
            ]
            for r in students
        ]
        self._export_result("at_risk_students.pdf", "At-Risk Students — KPIs", headers, rows, "pdf")

    # ── 5. Topper List (PDF) ───────────────────────────────────────

    def _export_toppers(self):
        subq = (
            self.db_session.query(
                Result.student_id,
                func.avg(Result.marks_obtained * 1.0 / func.nullif(Result.total_marks, 0)).label(
                    "avg_pct"
                ),
                func.count(Result.id).label("exams_taken"),
            )
            .filter(Result.is_deleted == False)
            .group_by(Result.student_id)
            .subquery()
        )

        records = (
            self.db_session.query(
                Student.enrollment_no,
                Student.first_name,
                Student.last_name,
                Course.name.label("course"),
                subq.c.avg_pct,
                subq.c.exams_taken,
            )
            .join(subq, Student.id == subq.c.student_id)
            .outerjoin(Course, Student.course_id == Course.id)
            .order_by(subq.c.avg_pct.desc().nullslast())
            .limit(100)
            .all()
        )

        headers = ["Rank", "Enrollment", "Name", "Course", "Avg Marks %", "Exams Taken"]
        rows = [
            [
                i + 1,
                r.enrollment_no,
                f"{r.first_name} {r.last_name}",
                r.course or "-",
                f"{round(r.avg_pct * 100, 1)}%" if r.avg_pct else "N/A",
                r.exams_taken,
            ]
            for i, r in enumerate(records)
        ]
        self._export_result("topper_list.pdf", "Topper List", headers, rows, "pdf")

    # ── 6. Staff Attendance (Excel) ────────────────────────────────

    def _export_staff_attendance(self):
        records = (
            self.db_session.query(
                Staff.first_name,
                Staff.last_name,
                Staff.department,
                StaffAttendance.date,
                StaffAttendance.status,
                StaffAttendance.in_time,
                StaffAttendance.out_time,
            )
            .select_from(StaffAttendance)
            .join(Staff, StaffAttendance.staff_id == Staff.id)
            .order_by(StaffAttendance.date.desc(), Staff.department)
            .limit(5000)
            .all()
        )
        headers = [
            "First Name",
            "Last Name",
            "Department",
            "Date",
            "Status",
            "In Time",
            "Out Time",
        ]
        rows = [
            [
                r.first_name,
                r.last_name,
                r.department or "-",
                str(r.date),
                r.status.value if r.status else "-",
                str(r.in_time) if r.in_time else "-",
                str(r.out_time) if r.out_time else "-",
            ]
            for r in records
        ]
        self._export_result("staff_attendance.xlsx", "Staff Attendance", headers, rows, "xlsx")

    # ── 7. Placement Summary (PDF) ─────────────────────────────────

    def _export_placements(self):
        records = (
            self.db_session.query(
                Student.enrollment_no,
                Student.first_name,
                Student.last_name,
                Placement.company_name,
                Placement.job_title,
                Placement.package_lpa,
                Placement.offer_date,
            )
            .select_from(Placement)
            .join(Student, Placement.student_id == Student.id)
            .order_by(Placement.offer_date.desc())
            .all()
        )
        headers = [
            "Enrollment",
            "Name",
            "Company",
            "Job Title",
            "Package (LPA)",
            "Offer Date",
        ]
        rows = [
            [
                r.enrollment_no,
                f"{r.first_name} {r.last_name}",
                r.company_name,
                r.job_title,
                r.package_lpa,
                str(r.offer_date) if r.offer_date else "-",
            ]
            for r in records
        ]
        self._export_result("placement_summary.pdf", "Placement Summary", headers, rows, "pdf")

    # ── 8. Course Enrollment (Excel) ───────────────────────────────

    def _export_enrollment(self):
        records = (
            self.db_session.query(
                Course.code,
                Course.name,
                func.count(Student.id).label("student_count"),
                func.sum(func.nullif(Fee.total_amount, 0)).label("total_collection"),
            )
            .outerjoin(Student, Student.course_id == Course.id)
            .outerjoin(Fee, (Fee.student_id == Student.id) & (Fee.is_deleted == False))
            .group_by(Course.id, Course.code, Course.name)
            .order_by(Course.code)
            .all()
        )
        headers = [
            "Course Code",
            "Course Name",
            "Enrolled Students",
            "Total Collection (₹)",
        ]
        rows = [
            [
                r.code,
                r.name,
                r.student_count,
                round(r.total_collection or 0, 2),
            ]
            for r in records
        ]
        self._export_result("course_enrollment.xlsx", "Course Enrollment", headers, rows, "xlsx")
