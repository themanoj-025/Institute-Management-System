import customtkinter as ctk

from services.leave_service import LeaveService
from ui.data_table import DataTable
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class LeaveManager(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.leave_service = LeaveService(db_session)

        ctk.CTkLabel(self, text="Leave Manager", font=self.tm.header_font).pack(pady=20, anchor="w")

        self.table = DataTable(
            self,
            columns=["ID", "Applicant", "Start", "End", "Status"],
            data=[],
            on_row_click=self._on_row_click,
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self):
        def fetch():
            res = self.leave_service.get_all_leaves()
            return [
                [
                    leave["id"],
                    leave["applicant"],
                    leave["start_date"],
                    leave["end_date"],
                    leave["status"],
                ]
                for leave in res
            ]

        def on_success(data):
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)

    def _on_row_click(self, row_data):
        leave_id = row_data[0]
        current_status = row_data[4].lower() if len(row_data) > 4 else ""

        # Don't re-approve already approved/rejected leaves
        if current_status in ("approved", "rejected"):
            ToastManager.show(
                self.winfo_toplevel(),
                f"Leave #{leave_id} already {current_status}",
                "warning",
            )
            return

        # Ask for confirmation
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Approve Leave?")
        dialog.geometry("350x180")
        dialog.grab_set()
        dialog.focus()
        dialog.attributes("-topmost", True)

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame,
            text=f"Approve Leave Request #{leave_id}?",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(10, 5))
        ctk.CTkLabel(frame, text=f"Applicant: {row_data[1]}", text_color="gray").pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=5)

        def approve():
            dialog.destroy()
            self.leave_service.approve_leave(leave_id, self.app_state.current_user["id"])
            ToastManager.show(self.winfo_toplevel(), f"Leave #{leave_id} Approved", "success")
            self._load_data()

        def reject():
            dialog.destroy()
            self.leave_service.reject_leave(leave_id, self.app_state.current_user["id"])
            ToastManager.show(self.winfo_toplevel(), f"Leave #{leave_id} Rejected", "info")
            self._load_data()

        def cancel():
            dialog.destroy()

        ctk.CTkButton(
            btn_frame,
            text="✅ Approve",
            command=approve,
            fg_color=self.tm.success_color,
            width=100,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame,
            text="❌ Reject",
            command=reject,
            fg_color=self.tm.danger_color,
            width=100,
        ).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel, fg_color="gray", width=80).pack(
            side="left", padx=5
        )
