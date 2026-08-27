from sqlalchemy.exc import SQLAlchemyError

import customtkinter as ctk

from services.feedback_service import FeedbackService
from ui.toast import ToastManager


class FeedbackSender(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.feedback_service = FeedbackService(db_session)

        ctk.CTkLabel(self, text="Send Feedback / Report Issue", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        # Card style
        form_card = ctk.CTkFrame(self, corner_radius=10)
        form_card.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(form_card, text="Category:").pack(anchor="w", padx=20, pady=(15, 0))
        self.cat_cb = ctk.CTkComboBox(
            form_card,
            values=[
                "General",
                "Academic",
                "Infrastructure",
                "Administrative Issues",
                "Resource Request",
            ],
            corner_radius=6,
        )
        self.cat_cb.pack(fill="x", padx=20, pady=5)
        self.cat_cb.set("General")

        ctk.CTkLabel(form_card, text="Message:").pack(anchor="w", padx=20, pady=(10, 0))
        self.msg_txt = ctk.CTkTextbox(form_card, height=150, corner_radius=8)
        self.msg_txt.pack(fill="x", padx=20, pady=5)

        self.submit_btn = ctk.CTkButton(
            form_card, text="Submit Feedback", command=self._submit, height=40
        )
        self.submit_btn.pack(pady=(15, 20))

    def _submit(self) -> None:
        msg = self.msg_txt.get("1.0", "end").strip()
        category = self.cat_cb.get()

        if not msg:
            ToastManager.show(self.winfo_toplevel(), "Message is required", "error")
            return

        try:
            user = self.app_state.current_user
            self.feedback_service.submit_feedback(user["id"], category, msg)
            ToastManager.show(
                self.winfo_toplevel(), "Feedback submitted successfully ✅", "success"
            )
            self.msg_txt.delete("1.0", "end")
        except (SQLAlchemyError, ValueError) as e:
            ToastManager.show(self.winfo_toplevel(), f"Failed to submit: {e}", "error")
