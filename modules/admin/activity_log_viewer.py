import customtkinter as ctk

from database.models import ActivityLog
from ui.data_table import DataTable
from utils.async_loader import AsyncLoader


class ActivityLogViewer(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.db_session = db_session

        ctk.CTkLabel(self, text="Activity Logs", font=self.tm.header_font).pack(pady=20, anchor="w")

        self.table = DataTable(
            self,
            columns=["ID", "User", "Action", "Module", "IP Address", "Timestamp"],
            data=[],
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self):
        self.table.show_loading()

        def fetch():
            logs = (
                self.db_session.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(100).all()
            )
            return [
                [
                    log.id,
                    log.user.username if log.user else "System",
                    log.action or "N/A",
                    log.module or "N/A",
                    log.ip_address or "N/A",
                    log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "N/A",
                ]
                for log in logs
            ]

        def on_success(data):
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)
