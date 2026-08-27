from sqlalchemy.exc import SQLAlchemyError

from datetime import date, datetime

import customtkinter as ctk
from tkinter import TclError

from services.placement_service import PlacementService
from services.student_service import StudentService
from ui.data_table import DataTable
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class PlacementManager(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.placement_service = PlacementService(db_session)
        self.student_service = StudentService(db_session)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=20)

        ctk.CTkLabel(header_frame, text="Placement Manager", font=self.tm.header_font).pack(
            side="left"
        )
        ctk.CTkButton(
            header_frame,
            text="+ Create Placement",
            command=self._create_placement,
            fg_color=self.tm.success_color,
            text_color=("black", "white"),
            hover_color=self.tm.info_color,
        ).pack(side="right")

        self.table = DataTable(
            self,
            columns=[
                "ID",
                "Student",
                "Company",
                "Job Title",
                "Package (LPA)",
                "Offer Date",
            ],
            data=[],
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            res = self.placement_service.get_all_placements()
            return [
                [
                    p["id"],
                    p.get("student_name", "N/A"),
                    p.get("company_name", "N/A"),
                    p.get("job_title", "N/A"),
                    f"{p.get('package_lpa', 0):.1f} LPA",
                    p.get("offer_date", "N/A"),
                ]
                for p in res
            ]

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)

    def _create_placement(self) -> None:
        """Open a dialog to create a new placement record."""
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Create New Placement")
        dialog.geometry("480x540")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.focus()
        dialog.attributes("-topmost", True)

        # Center on parent
        dialog.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() - 480) // 2
            y = self.winfo_rooty() + (self.winfo_height() - 540) // 2
            dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        except (TclError, RuntimeError):
            pass

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(
            frame, text="New Placement Record", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(0, 15))

        # ── Student Selector ──
        ctk.CTkLabel(frame, text="Student *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        students_res = self.student_service.get_all_students(limit=200)
        student_options = {
            f"{s['full_name']} ({s['enrollment_no']})": s["id"]
            for s in students_res.get("students", [])
        }
        student_names = list(student_options.keys())
        student_cb = ctk.CTkComboBox(
            frame,
            values=student_names if student_names else ["No students available"],
            width=420,
        )
        student_cb.pack(pady=(3, 8))
        if student_names:
            student_cb.set(student_names[0])

        # ── Company Name ──
        ctk.CTkLabel(frame, text="Company Name *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        company_entry = ctk.CTkEntry(
            frame, placeholder_text="e.g. Google, Microsoft, Amazon", width=420
        )
        company_entry.pack(pady=(3, 8))

        # ── Job Title ──
        ctk.CTkLabel(frame, text="Job Title *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        title_entry = ctk.CTkEntry(
            frame, placeholder_text="e.g. Software Engineer, Data Analyst", width=420
        )
        title_entry.pack(pady=(3, 8))

        # ── Package (LPA) ──
        ctk.CTkLabel(frame, text="Package (LPA) *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        package_entry = ctk.CTkEntry(frame, placeholder_text="e.g. 12.5", width=420)
        package_entry.pack(pady=(3, 8))

        # ── Offer Date ──
        ctk.CTkLabel(
            frame, text="Offer Date (YYYY-MM-DD) *", anchor="w", font=self.tm.main_font
        ).pack(fill="x", pady=(5, 0))
        date_entry = ctk.CTkEntry(frame, placeholder_text="e.g. 2026-07-26", width=420)
        date_entry.pack(pady=(3, 12))
        date_entry.insert(0, date.today().isoformat())

        # ── Error label (hidden) ──
        error_lbl = ctk.CTkLabel(
            frame, text="", text_color=self.tm.danger_color, font=self.tm.small_font
        )
        error_lbl.pack(pady=(0, 5))

        # ── Buttons ──
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(5, 0))

        def submit() -> None:
            # Validate
            selected_student = student_cb.get()
            company = company_entry.get().strip()
            title = title_entry.get().strip()
            package_str = package_entry.get().strip()
            offer_date_str = date_entry.get().strip()

            if selected_student not in student_options:
                error_lbl.configure(text="Please select a valid student.")
                return
            if not company:
                error_lbl.configure(text="Company name is required.")
                return
            if not title:
                error_lbl.configure(text="Job title is required.")
                return
            try:
                package = float(package_str)
                if package <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                error_lbl.configure(text="Package must be a positive number (e.g. 12.5).")
                return
            try:
                offer_date = datetime.strptime(offer_date_str, "%Y-%m-%d").date()
            except ValueError:
                error_lbl.configure(text="Offer date must be in YYYY-MM-DD format.")
                return

            student_id = student_options[selected_student]
            try:
                self.placement_service.create_placement(
                    student_id=student_id,
                    company_name=company,
                    job_title=title,
                    package_lpa=package,
                    offer_date=offer_date,
                )
                dialog.destroy()
                ToastManager.show(
                    self.winfo_toplevel(),
                    f"Placement created for {selected_student.split(' (')[0]} at {company} ✅",
                    "success",
                )
                self._load_data()
            except (SQLAlchemyError, ValueError) as e:
                error_lbl.configure(text=f"Failed to create: {e}")

        ctk.CTkButton(
            btn_frame,
            text="✅ Create Placement",
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
