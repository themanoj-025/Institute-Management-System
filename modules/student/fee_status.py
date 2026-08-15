import customtkinter as ctk

from services.fee_service import FeeService
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class FeeStatus(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.fee_service = FeeService(db_session)
        self.app_state = app_state

        ctk.CTkLabel(self, text="Fee Status", font=self.tm.header_font).pack(pady=20, anchor="w")

        # Fee summary card
        self.card = ctk.CTkFrame(
            self, corner_radius=12, border_width=2, border_color=self.tm.accent_color
        )
        self.card.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(
            self.card,
            text="Fee Summary",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(15, 10), padx=20, anchor="w")

        self._summary_labels = {}
        for label in ["Total Fee", "Paid Amount", "Balance", "Status"]:
            row = ctk.CTkFrame(self.card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=3)
            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=13), text_color="gray").pack(
                side="left"
            )
            val_lbl = ctk.CTkLabel(
                row,
                text="—",
                font=ctk.CTkFont(size=13, weight="bold"),
            )
            val_lbl.pack(side="right")
            self._summary_labels[label] = val_lbl

        ctk.CTkButton(
            self.card,
            text="📄 Download Receipt",
            fg_color=self.tm.accent_color,
            width=200,
            height=38,
            command=self._download_receipt,
        ).pack(pady=(15, 20))

        # Payment history
        self.history_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.history_frame.pack(fill="both", expand=True, pady=(20, 10))

        ctk.CTkLabel(
            self.history_frame,
            text="💳 Payment History",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 5), padx=10, anchor="w")

        self._history_content = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        self._history_content.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(
            self._history_content,
            text="Loading payment records...",
            text_color="gray",
        ).pack(pady=20)

        # Auto-load
        self.after(300, self._load_fee_data)

    def _load_fee_data(self):
        student_id = self.app_state.current_user.get("profile_id")
        if not student_id:
            ctk.CTkLabel(
                self._history_content,
                text="Student profile not found.",
                text_color="gray",
            ).pack(pady=20)
            return

        AsyncLoader.run(
            self,
            lambda: self.fee_service.get_student_fees(student_id),
            self._render_fee_data,
        )

    def _render_fee_data(self, fees):
        for w in self._history_content.winfo_children():
            w.destroy()

        if not fees:
            self._summary_labels["Total Fee"].configure(text="₹0")
            self._summary_labels["Paid Amount"].configure(text="₹0")
            self._summary_labels["Balance"].configure(text="₹0")
            self._summary_labels["Status"].configure(text="No Records")
            ctk.CTkLabel(
                self._history_content,
                text="No fee records found for your account.",
                text_color="gray",
            ).pack(pady=20)
            return

        # Aggregate all fee records
        total_fee = sum(f["total_amount"] for f in fees)
        total_paid = sum(f["paid_amount"] for f in fees)
        total_balance = sum(f["balance"] for f in fees)
        statuses = [f["status"] for f in fees]
        overall_status = (
            "Paid"
            if all(s == "paid" for s in statuses)
            else ("Partial" if any(s == "partial" for s in statuses) else "Unpaid")
        )

        status_color = (
            self.tm.success_color
            if overall_status == "Paid"
            else (self.tm.warning_color if overall_status == "Partial" else self.tm.danger_color)
        )

        self._summary_labels["Total Fee"].configure(
            text=f"₹{total_fee:,.0f}", text_color=self.tm.accent_color
        )
        self._summary_labels["Paid Amount"].configure(
            text=f"₹{total_paid:,.0f}", text_color=self.tm.success_color
        )
        self._summary_labels["Balance"].configure(
            text=f"₹{total_balance:,.0f}",
            text_color=(self.tm.success_color if total_balance <= 0 else self.tm.danger_color),
        )
        self._summary_labels["Status"].configure(text=overall_status, text_color=status_color)

        # Payment history per fee record
        for fee_idx, fee in enumerate(fees):
            if fee_idx > 0:
                ctk.CTkFrame(self._history_content, height=1, fg_color="gray").pack(
                    fill="x", pady=8
                )

            # Fee header
            fee_header = ctk.CTkFrame(self._history_content, fg_color="transparent")
            fee_header.pack(fill="x", pady=(5, 2))
            ctk.CTkLabel(
                fee_header,
                text=fee.get("student_name", "Fee Record"),
                font=ctk.CTkFont(weight="bold", size=13),
            ).pack(side="left")
            due = fee.get("due_date", "—")
            ctk.CTkLabel(
                fee_header,
                text=f"Due: {due}",
                font=ctk.CTkFont(size=11),
                text_color="gray",
            ).pack(side="right")

            # Fee details row
            detail_row = ctk.CTkFrame(self._history_content, fg_color="transparent")
            detail_row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                detail_row,
                text=f"Total: ₹{fee['total_amount']:,.0f}",
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 15))
            ctk.CTkLabel(
                detail_row,
                text=f"Paid: ₹{fee['paid_amount']:,.0f}",
                font=ctk.CTkFont(size=12),
                text_color=self.tm.success_color,
            ).pack(side="left", padx=(0, 15))
            ctk.CTkLabel(
                detail_row,
                text=f"Balance: ₹{fee['balance']:,.0f}",
                font=ctk.CTkFont(size=12),
                text_color=self.tm.danger_color if fee["balance"] > 0 else self.tm.success_color,
            ).pack(side="left")

            # Status badge
            s_badge = ctk.CTkLabel(
                detail_row,
                text=fee["status"].upper(),
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=status_color,
            )
            s_badge.pack(side="right")

    def _download_receipt(self):
        ToastManager.show(
            self.winfo_toplevel(),
            "Receipt download will be available in a future update.",
            "info",
        )
