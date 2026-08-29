from datetime import date, datetime

import customtkinter as ctk
from sqlalchemy.exc import SQLAlchemyError

from services.leave_service import LeaveService
from ui.toast import ToastManager


class LeaveApply(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.leave_service = LeaveService(db_session)

        ctk.CTkLabel(self, text="Apply for Leave", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        # Card style form
        form_card = ctk.CTkFrame(self, corner_radius=10)
        form_card.pack(fill="x", pady=10, padx=10)

        # Date range
        date_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        date_frame.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(date_frame, text="From:").pack(side="left", padx=(0, 5))
        self.start_entry = ctk.CTkEntry(date_frame, placeholder_text="YYYY-MM-DD", width=130)
        self.start_entry.pack(side="left", padx=5)

        ctk.CTkLabel(date_frame, text="To:").pack(side="left", padx=(10, 5))
        self.end_entry = ctk.CTkEntry(date_frame, placeholder_text="YYYY-MM-DD", width=130)
        self.end_entry.pack(side="left", padx=5)

        # Pre-fill with sensible defaults
        today = date.today()
        self.start_entry.insert(0, today.isoformat())

        # Reason
        ctk.CTkLabel(form_card, text="Reason:").pack(anchor="w", padx=20, pady=(10, 0))
        self.reason_txt = ctk.CTkTextbox(form_card, height=120, corner_radius=8)
        self.reason_txt.pack(fill="x", padx=20, pady=5)

        self.submit_btn = ctk.CTkButton(
            form_card, text="Submit Leave Application", command=self._submit, height=40
        )
        self.submit_btn.pack(pady=(15, 20))

    def _submit(self) -> None:
        reason = self.reason_txt.get("1.0", "end").strip()
        start_str = self.start_entry.get().strip()
        end_str = self.end_entry.get().strip()

        if not reason:
            ToastManager.show(self.winfo_toplevel(), "Reason is required", "error")
            return

        if not start_str or not end_str:
            ToastManager.show(self.winfo_toplevel(), "Please enter start and end dates", "error")
            return

        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            ToastManager.show(self.winfo_toplevel(), "Invalid date format. Use YYYY-MM-DD", "error")
            return

        if end_date < start_date:
            ToastManager.show(self.winfo_toplevel(), "End date must be after start date", "error")
            return

        try:
            user = self.app_state.current_user
            data = {"start_date": start_date, "end_date": end_date, "reason": reason}

            if user.get("role") == "student":
                data["student_id"] = user.get("profile_id", 1)
            else:
                data["staff_id"] = user.get("profile_id", 1)

            self.leave_service.apply_leave(data)
            ToastManager.show(self.winfo_toplevel(), "Leave applied successfully ✅", "success")
            self.reason_txt.delete("1.0", "end")
        except (SQLAlchemyError, ValueError) as e:
            ToastManager.show(self.winfo_toplevel(), f"Failed to apply leave: {e}", "error")
