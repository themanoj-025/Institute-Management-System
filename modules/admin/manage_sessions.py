import customtkinter as ctk

from database.models import Session as AcadSession
from ui.data_table import DataTable
from utils.async_loader import AsyncLoader


class ManageSessions(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.db_session = db_session

        ctk.CTkLabel(self, text="Manage Sessions", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        self.table = DataTable(
            self, columns=["ID", "Name", "Start Date", "End Date", "Status"], data=[]
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            sessions = self.db_session.query(AcadSession).all()
            data = []
            for s in sessions:
                try:
                    status = "✅ Active" if s.is_active else "🔒 Closed"
                    data.append(
                        [
                            s.id,
                            s.name or "N/A",
                            s.start_date.isoformat() if s.start_date else "N/A",
                            s.end_date.isoformat() if s.end_date else "N/A",
                            status,
                        ]
                    )
                except Exception:
                    data.append([s.id, "N/A", "N/A", "N/A", "N/A"])
            return data

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)
