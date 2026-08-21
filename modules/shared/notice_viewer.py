import customtkinter as ctk

from services.notice_service import NoticeService
from utils.async_loader import AsyncLoader


class NoticeViewer(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.notice_service = NoticeService(db_session)

        ctk.CTkLabel(self, text="Notice Board", font=self.tm.header_font).pack(pady=20, anchor="w")

        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)

        # Load notices
        self._load_notices()

    def _load_notices(self) -> None:
        # Show loading
        for w in self.scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.scroll, text="⏳ Loading notices...", text_color="gray").pack(pady=30)

        def fetch() -> None:
            role = (
                self.app_state.current_user.get("role", "student")
                if self.app_state.current_user
                else "student"
            )
            return self.notice_service.get_all_notices(target_role=role)

        def on_success(notices) -> None:
            for w in self.scroll.winfo_children():
                w.destroy()

            if not notices:
                ctk.CTkLabel(
                    self.scroll,
                    text="📢 No notices available",
                    font=ctk.CTkFont(size=14),
                    text_color="gray",
                ).pack(pady=40)
                return

            for notice in notices:
                card = ctk.CTkFrame(
                    self.scroll, corner_radius=8, border_width=1, border_color="gray30"
                )
                card.pack(fill="x", pady=6, padx=5)

                header = ctk.CTkFrame(card, fg_color="transparent")
                header.pack(fill="x", padx=15, pady=(12, 5))

                pin_icon = "📌 " if notice.get("is_pinned") else ""
                ctk.CTkLabel(
                    header,
                    text=f"{pin_icon}{notice['title']}",
                    font=ctk.CTkFont(size=15, weight="bold"),
                ).pack(side="left")
                ctk.CTkLabel(
                    header,
                    text=notice.get("date", ""),
                    font=ctk.CTkFont(size=11),
                    text_color="gray",
                ).pack(side="right")

                ctk.CTkLabel(
                    card, text=notice.get("content", ""), wraplength=700, justify="left"
                ).pack(anchor="w", padx=15, pady=(0, 10))

                author_lbl = ctk.CTkLabel(
                    card,
                    text=f"— {notice.get('author', 'Unknown')}",
                    font=ctk.CTkFont(size=11),
                    text_color="gray",
                )
                author_lbl.pack(anchor="e", padx=15, pady=(0, 10))

        AsyncLoader.run(self, fetch, on_success)
