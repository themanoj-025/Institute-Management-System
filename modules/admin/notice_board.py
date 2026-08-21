import customtkinter as ctk

from services.notice_service import NoticeService
from ui.data_table import DataTable
from ui.toast import ToastManager
from utils.async_loader import AsyncLoader


class NoticeBoard(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.notice_service = NoticeService(db_session)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=20)

        ctk.CTkLabel(header_frame, text="Notice Board Management", font=self.tm.header_font).pack(
            side="left"
        )
        ctk.CTkButton(header_frame, text="+ Create Notice", command=self._create_notice).pack(
            side="right"
        )

        self.table = DataTable(
            self,
            columns=["ID", "Title", "Author", "Date", "Target Role", "Pinned"],
            data=[],
        )
        self.table.pack(fill="both", expand=True)

        self._load_data()

    def _load_data(self) -> None:
        self.table.show_loading()

        def fetch() -> None:
            res = self.notice_service.get_all_notices()
            return [
                [
                    n["id"],
                    n["title"],
                    n.get("author", "Unknown"),
                    n.get("date", ""),
                    n.get("target_role", "all"),
                    "📌" if n.get("is_pinned") else "",
                ]
                for n in res
            ]

        def on_success(data) -> None:
            self.table.update_data(data)

        AsyncLoader.run(self, fetch, on_success)

    def _create_notice(self) -> None:
        """Open a dialog to create a new notice."""
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Create New Notice")
        dialog.geometry("500x520")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.focus()
        dialog.attributes("-topmost", True)

        # Center on parent
        dialog.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() - 500) // 2
            y = self.winfo_rooty() + (self.winfo_height() - 520) // 2
            dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        ctk.CTkLabel(
            frame, text="Create New Notice", font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(0, 15))

        # Title
        ctk.CTkLabel(frame, text="Notice Title *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        title_entry = ctk.CTkEntry(frame, placeholder_text="Enter notice title", width=440)
        title_entry.pack(pady=(3, 10))

        # Content
        ctk.CTkLabel(frame, text="Notice Content *", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        content_txt = ctk.CTkTextbox(frame, height=160, width=440, corner_radius=8)
        content_txt.pack(pady=(3, 10))

        # Target Role
        ctk.CTkLabel(frame, text="Target Audience", anchor="w", font=self.tm.main_font).pack(
            fill="x", pady=(5, 0)
        )
        role_cb = ctk.CTkComboBox(frame, values=["all", "staff", "student"], width=440)
        role_cb.pack(pady=(3, 5))
        role_cb.set("all")

        # Pinned toggle
        pinned_var = ctk.BooleanVar(value=False)
        pinned_switch = ctk.CTkSwitch(
            frame, text="📌 Pin this notice (appears at top)", variable=pinned_var
        )
        pinned_switch.pack(anchor="w", pady=(5, 10))

        # Error label
        error_lbl = ctk.CTkLabel(
            frame, text="", text_color=self.tm.danger_color, font=self.tm.small_font
        )
        error_lbl.pack(pady=(0, 5))

        # Buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=(5, 0))

        def submit() -> None:
            title = title_entry.get().strip()
            content = content_txt.get("1.0", "end").strip()
            target_role = role_cb.get()
            is_pinned = pinned_var.get()

            if not title:
                error_lbl.configure(text="Notice title is required.")
                return
            if not content:
                error_lbl.configure(text="Notice content is required.")
                return

            try:
                author_id = self.app_state.current_user["id"]
                self.notice_service.create_notice(
                    title=title,
                    content=content,
                    author_id=author_id,
                    target_role=target_role,
                    is_pinned=is_pinned,
                )
                dialog.destroy()
                ToastManager.show(
                    self.winfo_toplevel(),
                    f"Notice '{title}' published successfully ✅",
                    "success",
                )
                self._load_data()
            except Exception as e:
                error_lbl.configure(text=f"Failed to create notice: {e}")

        ctk.CTkButton(
            btn_frame,
            text="📢 Publish Notice",
            command=submit,
            fg_color=self.tm.accent_color,
            width=160,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color="gray",
            width=100,
        ).pack(side="left", padx=6)
