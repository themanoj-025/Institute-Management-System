import customtkinter as ctk

from services.fee_service import FeeService
from ui.data_table import DataTable
from utils.async_loader import AsyncLoader


class FeeManagement(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.fee_service = FeeService(db_session)

        ctk.CTkLabel(self, text="Fee Management", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        self.table = DataTable(
            self,
            columns=["ID", "Student Name", "Total", "Paid", "Balance", "Status"],
            data=[],
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            res = self.fee_service.get_all_fees()
            return [
                [
                    f["id"],
                    f.get("student_name", "N/A"),
                    f"₹{f.get('total_amount', 0):,.0f}",
                    f"₹{f.get('paid_amount', 0):,.0f}",
                    f"₹{f.get('balance', 0):,.0f}",
                    f.get("status", "N/A"),
                ]
                for f in res
            ]

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)
