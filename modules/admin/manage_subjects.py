import customtkinter as ctk

from database.models import Subject
from ui.data_table import DataTable
from utils.async_loader import AsyncLoader


class ManageSubjects(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs):
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.db_session = db_session

        ctk.CTkLabel(self, text="Manage Subjects", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        self.table = DataTable(
            self, columns=["ID", "Code", "Name", "Course", "Assigned Staff"], data=[]
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self):
        self.table.show_loading()

        def fetch():
            subjects = self.db_session.query(Subject).all()
            data = []
            for s in subjects:
                try:
                    staff_name = (
                        f"{s.staff.first_name} {s.staff.last_name}" if s.staff else "Unassigned"
                    )
                except Exception:
                    staff_name = "Unassigned"
                try:
                    course_code = s.course.code if s.course else "Unknown"
                except Exception:
                    course_code = "Unknown"
                data.append([s.id, s.code, s.name, course_code, staff_name])
            return data

        def on_success(data):
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)
