from datetime import date, datetime

import customtkinter as ctk
from tkinter import TclError

from services.staff_service import StaffService
from ui.data_table import DataTable
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class ManageStaff(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.staff_service = StaffService(db_session)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=20)

        ctk.CTkLabel(header_frame, text="Manage Staff", font=self.tm.header_font).pack(side="left")
        ctk.CTkButton(
            header_frame,
            text="+ Add Staff",
            command=self._add_staff,
            fg_color=self.tm.success_color,
            text_color=("black", "white"),
            hover_color=self.tm.info_color,
        ).pack(side="right")

        self.table = DataTable(
            self,
            columns=["ID", "Name", "Department", "Designation", "Join Date"],
            data=[],
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            res = self.staff_service.get_all_staff(limit=25)
            return [
                [
                    s["id"],
                    s["full_name"],
                    s.get("department", "N/A"),
                    s.get("designation", "N/A"),
                    s.get("join_date", "N/A"),
                ]
                for s in res.get("staff", [])
            ]

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)

    def _add_staff(self) -> None:
        """Open a dialog to add a new staff member."""
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Add New Staff")
        dialog.geometry("480x560")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.focus()
        dialog.attributes("-topmost", True)

        # Center on parent
        dialog.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() - 480) // 2
            y = self.winfo_rooty() + (self.winfo_height() - 560) // 2
            dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        except (TclError, RuntimeError):
            pass

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(
            frame, text="Add New Staff Member", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(0, 15))

        # ── First Name ──
        ctk.CTkLabel(frame, text="First Name *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        first_name_entry = ctk.CTkEntry(frame, placeholder_text="First name", width=420)
        first_name_entry.pack(pady=(3, 6))

        # ── Last Name ──
        ctk.CTkLabel(frame, text="Last Name *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        last_name_entry = ctk.CTkEntry(frame, placeholder_text="Last name", width=420)
        last_name_entry.pack(pady=(3, 6))

        # ── Email ──
        ctk.CTkLabel(frame, text="Email *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        email_entry = ctk.CTkEntry(frame, placeholder_text="staff@example.com", width=420)
        email_entry.pack(pady=(3, 6))

        # ── Phone ──
        ctk.CTkLabel(frame, text="Phone", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        phone_entry = ctk.CTkEntry(frame, placeholder_text="10-digit mobile number", width=420)
        phone_entry.pack(pady=(3, 6))

        # ── Department ──
        ctk.CTkLabel(frame, text="Department", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        dept_entry = ctk.CTkEntry(frame, placeholder_text="e.g. Computer Science", width=420)
        dept_entry.pack(pady=(3, 6))

        # ── Designation ──
        ctk.CTkLabel(frame, text="Designation", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        desig_entry = ctk.CTkEntry(
            frame, placeholder_text="e.g. Professor, Assistant Professor", width=420
        )
        desig_entry.pack(pady=(3, 6))

        # ── Join Date ──
        ctk.CTkLabel(
            frame, text="Join Date (YYYY-MM-DD) *", anchor="w", font=self.tm.main_font
        ).pack(fill="x", pady=(3, 0))
        join_entry = ctk.CTkEntry(frame, placeholder_text="e.g. 2026-01-15", width=420)
        join_entry.pack(pady=(3, 6))
        join_entry.insert(0, date.today().isoformat())

        # ── Salary ──
        ctk.CTkLabel(frame, text="Salary (₹)", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(3, 0)
        )
        salary_entry = ctk.CTkEntry(frame, placeholder_text="e.g. 50000", width=420)
        salary_entry.pack(pady=(3, 10))

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
            department = dept_entry.get().strip()
            designation = desig_entry.get().strip()
            join_str = join_entry.get().strip()
            salary_str = salary_entry.get().strip()

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
            try:
                join_date = datetime.strptime(join_str, "%Y-%m-%d").date()
            except ValueError:
                error_lbl.configure(text="Join date must be in YYYY-MM-DD format.")
                return

            salary = 0.0
            if salary_str:
                try:
                    salary = float(salary_str)
                except ValueError:
                    error_lbl.configure(text="Salary must be a number.")
                    return

            username = email.split("@")[0]

            try:
                self.staff_service.create_staff(
                    {
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "phone": phone or None,
                        "department": department or None,
                        "designation": designation or None,
                        "join_date": join_date,
                        "salary": salary,
                    }
                )
                dialog.destroy()
                ToastManager.show(
                    self.winfo_toplevel(),
                    f"Staff {first_name} {last_name} added successfully ✅",
                    "success",
                )
                self._load_data()
            except Exception as e:
                error_lbl.configure(text=f"Failed to add staff: {e}")

        ctk.CTkButton(
            btn_frame,
            text="✅ Add Staff",
            command=submit,
            fg_color=self.tm.success_color,
            text_color=("black", "white"),
            width=140,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color="gray",
            width=100,
        ).pack(side="left", padx=6)
