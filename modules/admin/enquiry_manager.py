import customtkinter as ctk

from database.models import Enquiry
from ui.data_table import DataTable
from utils.async_loader import AsyncLoader


class EnquiryManager(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.db_session = db_session

        ctk.CTkLabel(self, text="Enquiry Manager", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        self.table = DataTable(
            self,
            columns=[
                "ID",
                "Name",
                "Email",
                "Phone",
                "Course Interest",
                "Date",
                "Status",
            ],
            data=[],
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            enquiries = self.db_session.query(Enquiry).order_by(Enquiry.id.desc()).all()
            return [
                [
                    e.id,
                    e.name or "N/A",
                    e.email or "N/A",
                    e.phone or "N/A",
                    e.course_interest or "N/A",
                    e.submitted_at.strftime("%Y-%m-%d") if e.submitted_at else "N/A",
                    "✅ Resolved" if e.is_resolved else "⏳ Pending",
                ]
                for e in enquiries
            ]

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)
