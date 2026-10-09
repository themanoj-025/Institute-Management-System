import customtkinter as ctk

from services.feedback_service import FeedbackService
from ui.data_table import DataTable
from utils.async_loader import AsyncLoader


class FeedbackViewer(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.feedback_service = FeedbackService(db_session)

        ctk.CTkLabel(self, text="Feedback Viewer", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        self.table = DataTable(
            self, columns=["ID", "Category", "User", "Submitted On", "Status"], data=[]
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            res = self.feedback_service.get_all_feedback()
            return [
                [
                    f["id"],
                    f.get("category", "N/A"),
                    f.get("user", "Unknown"),
                    f.get("submitted_on", "N/A")[:10],
                    "💬 Replied" if f.get("reply") else "⏳ Pending",
                ]
                for f in res
            ]

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)
