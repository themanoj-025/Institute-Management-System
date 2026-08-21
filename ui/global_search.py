import json
import os

import customtkinter as ctk

from services.search_service import SearchService

CATEGORY_ICONS = {
    "students": "🎓",
    "staff": "👥",
    "courses": "📖",
    "notices": "📢",
    "subjects": "🔬",
}


class GlobalSearch(ctk.CTkToplevel):
    def __init__(self, master, navigate_callback, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.navigate = navigate_callback
        self.db_session = master.db_session
        self.search_service = SearchService(self.db_session)

        self.title("Global Command Center")
        self.geometry("640x480")
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Center overlay
        x = master.winfo_rootx() + (master.winfo_width() - 640) // 2
        y = master.winfo_rooty() + (master.winfo_height() - 480) // 2
        self.geometry(f"+{x}+{y}")

        self.frame = ctk.CTkFrame(self, corner_radius=12, border_width=2, border_color="#89b4fa")
        self.frame.pack(fill="both", expand=True)

        # Top Bar
        self.top_bar = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=15, pady=(15, 5))

        self.search_icon = ctk.CTkLabel(self.top_bar, text="🔍", font=("Inter", 16))
        self.search_icon.pack(side="left", padx=(5, 10))

        self.entry = ctk.CTkEntry(
            self.top_bar,
            placeholder_text="Search students, staff, modules... (ESC to close)",
            font=("Inter", 14),
            height=40,
            fg_color="#1e1e2e" if ctk.get_appearance_mode().lower() == "dark" else "#eff1f5",
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.focus()

        self.esc_hint = ctk.CTkLabel(
            self.top_bar,
            text="ESC",
            font=("Inter", 10, "bold"),
            fg_color="#313244",
            text_color="#cdd6f4",
            corner_radius=4,
            width=30,
            height=20,
        )
        self.esc_hint.pack(side="right", padx=(10, 5))

        # Results Scrollable Container
        self.results_frame = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Bind events
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Up>", self._move_up)
        self.bind("<Down>", self._move_down)
        self.bind("<Return>", self._select_current)
        self.bind("<FocusOut>", lambda e: self.destroy())

        self.debounce_timer = None
        self.flat_items = []  # Stores (widget, result_row)
        self.selected_index = -1

        self.load_recent()
        self.show_recent()

    def load_recent(self) -> None:
        self.recent_items = []
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database",
            "settings.json",
        )
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    self.recent_items = json.load(f).get("recent_searches", [])
            except Exception:
                pass

    def save_recent(self, item) -> None:
        # Remove if exists
        self.recent_items = [r for r in self.recent_items if r.get("id") != item.get("id")]
        self.recent_items.insert(0, item)
        self.recent_items = self.recent_items[:5]

        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database",
            "settings.json",
        )
        try:
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    settings = json.load(f)
            settings["recent_searches"] = self.recent_items
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception:
            pass

    def _on_key_release(self, event) -> None:
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return

        if self.debounce_timer:
            self.after_cancel(self.debounce_timer)

        self.debounce_timer = self.after(250, self.perform_search)

    def perform_search(self) -> None:
        query = self.entry.get().strip()

        # Clear existing
        for child in self.results_frame.winfo_children():
            child.destroy()
        self.flat_items.clear()
        self.selected_index = -1

        if not query:
            self.show_recent()
            return

        if len(query) < 2:
            return

        results = self.search_service.global_search(query)

        has_results = False
        for cat, items in results.items():
            if items:
                has_results = True
                icon = CATEGORY_ICONS.get(cat, "🔹")

                # Category Header
                header = ctk.CTkLabel(
                    self.results_frame,
                    text=f"{icon} {cat.upper()} ({len(items)})",
                    font=("Inter", 12, "bold"),
                    text_color="#89b4fa",
                    anchor="w",
                )
                header.pack(fill="x", pady=(10, 2), padx=5)

                for item in items:
                    btn = ctk.CTkButton(
                        self.results_frame,
                        text=f"  {item['title']} — {item['subtitle']}",
                        anchor="w",
                        fg_color="transparent",
                        text_color=("black", "white"),
                        hover_color="#313244",
                        height=36,
                        command=lambda it=item: self._handle_click(it),
                    )
                    btn.pack(fill="x", pady=1)
                    self.flat_items.append((btn, item))

        if not has_results:
            empty_lbl = ctk.CTkLabel(
                self.results_frame,
                text=f"No results for '{query}'",
                font=("Inter", 13),
                text_color="#f38ba8",
                pady=20,
            )
            empty_lbl.pack()

    def show_recent(self) -> None:
        if not self.recent_items:
            recent_lbl = ctk.CTkLabel(
                self.results_frame,
                text="Type at least 2 characters to search...",
                font=("Inter", 13),
                text_color="gray",
                pady=20,
            )
            recent_lbl.pack()
            return

        header = ctk.CTkLabel(
            self.results_frame,
            text="⏰ RECENT ITEMS",
            font=("Inter", 12, "bold"),
            text_color="gray",
            anchor="w",
        )
        header.pack(fill="x", pady=(10, 2), padx=5)

        for item in self.recent_items:
            btn = ctk.CTkButton(
                self.results_frame,
                text=f"  {item['title']} — {item['subtitle']}",
                anchor="w",
                fg_color="transparent",
                text_color=("black", "white"),
                hover_color="#313244",
                height=36,
                command=lambda it=item: self._handle_click(it),
            )
            btn.pack(fill="x", pady=1)
            self.flat_items.append((btn, item))

    def _move_up(self, event) -> None:
        if not self.flat_items:
            return
        if self.selected_index > 0:
            self._highlight_item(self.selected_index - 1)

    def _move_down(self, event) -> None:
        if not self.flat_items:
            return
        if self.selected_index < len(self.flat_items) - 1:
            self._highlight_item(self.selected_index + 1)

    def _highlight_item(self, index) -> None:
        # Reset current selection
        if self.selected_index != -1:
            self.flat_items[self.selected_index][0].configure(fg_color="transparent")

        self.selected_index = index
        # Highlight new selection
        self.flat_items[self.selected_index][0].configure(fg_color="#313244")

    def _select_current(self, event) -> None:
        if self.selected_index != -1:
            item = self.flat_items[self.selected_index][1]
            self._handle_click(item)

    def _handle_click(self, item) -> None:
        self.save_recent(item)
        self.navigate(item["route"])
        self.destroy()
