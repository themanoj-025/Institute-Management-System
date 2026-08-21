import customtkinter as ctk

from services.course_service import CourseService
from ui.data_table import DataTable
from utils.async_loader import AsyncLoader


class ManageCourses(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.course_service = CourseService(db_session)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=20)

        ctk.CTkLabel(header_frame, text="Manage Courses", font=self.tm.header_font).pack(
            side="left"
        )

        self.table = DataTable(self, columns=["ID", "Code", "Name", "Duration", "Fee"], data=[])
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            res = self.course_service.get_all_courses()
            return [
                [
                    c["id"],
                    c.get("code", "N/A"),
                    c.get("name", "N/A"),
                    f"{c.get('duration', 0)} Months",
                    f"₹{c.get('fee', 0):,.0f}",
                ]
                for c in res
            ]

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)
