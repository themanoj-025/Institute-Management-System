import customtkinter as ctk

from services.student_service import StudentService
from utils.async_loader import AsyncLoader


class StudentLookup(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.student_service = StudentService(db_session)

        ctk.CTkLabel(self, text="Student Lookup", font=self.tm.header_font).pack(
            pady=20, anchor="w"
        )

        # Search bar
        search_frame = ctk.CTkFrame(self, corner_radius=8)
        search_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkLabel(search_frame, text="🔍", font=ctk.CTkFont(size=18)).pack(
            side="left", padx=(15, 5), pady=10
        )
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Enter Enrollment No or Name",
            width=350,
            height=38,
        )
        self.search_entry.pack(side="left", padx=5, pady=10)

        self.search_btn = ctk.CTkButton(
            search_frame, text="Search", width=100, height=38, command=self._do_search
        )
        self.search_btn.pack(side="left", padx=5, pady=10)

        # Tabs for details
        tabview = ctk.CTkTabview(self, corner_radius=10)
        tabview.pack(fill="both", expand=True, pady=10)

        tabview.add("👤 Profile")
        tabview.add("📅 Attendance")
        tabview.add("📊 Results")
        tabview.add("💳 Fees")
        tabview.add("✉ Leave History")

        ctk.CTkLabel(
            tabview.tab("👤 Profile"),
            text="Search a student to view their complete profile.",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(pady=50)
        ctk.CTkLabel(
            tabview.tab("📅 Attendance"),
            text="Attendance records will appear here after search.",
            text_color="gray",
        ).pack(pady=50)
        ctk.CTkLabel(
            tabview.tab("📊 Results"),
            text="Academic results will appear here after search.",
            text_color="gray",
        ).pack(pady=50)
        ctk.CTkLabel(
            tabview.tab("💳 Fees"),
            text="Fee details will appear here after search.",
            text_color="gray",
        ).pack(pady=50)
        ctk.CTkLabel(
            tabview.tab("✉ Leave History"),
            text="Leave records will appear here after search.",
            text_color="gray",
        ).pack(pady=50)

    def _do_search(self) -> None:
        query = self.search_entry.get().strip()
        if not query:
            from ui.toast import ToastManager

            ToastManager.show(self.winfo_toplevel(), "Please enter a search query", "warning")
            return

        # Search and show results
        def fetch() -> None:
            return self.student_service.get_all_students(limit=10, search_query=query)

        def on_success(results) -> None:
            from ui.toast import ToastManager

            count = results.get("total", 0)
            ToastManager.show(
                self.winfo_toplevel(),
                f"Found {count} student(s)",
                "success" if count > 0 else "warning",
            )

        AsyncLoader.run(self, fetch, on_success)
