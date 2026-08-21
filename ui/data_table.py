import customtkinter as ctk


class DataTable(ctk.CTkFrame):
    def __init__(self, master, columns, data, on_row_click=None, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.columns = columns
        self.on_row_click = on_row_click
        self._loading = False

        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=(0, 5))

        for i, col in enumerate(self.columns):
            self.header_frame.grid_columnconfigure(i, weight=1)
            lbl = ctk.CTkLabel(self.header_frame, text=col, font=ctk.CTkFont(weight="bold"))
            lbl.grid(row=0, column=i, sticky="w", padx=10, pady=5)

        # Data area (scrollable)
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True)

        self.update_data(data)

    def show_loading(self) -> None:
        """Show loading indicator while data is being fetched."""
        self._loading = True
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        load_lbl = ctk.CTkLabel(
            self.scroll_frame,
            text="⏳ Loading data...",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        load_lbl.pack(pady=30)
        self.update_idletasks()

    def update_data(self, data) -> None:
        if not hasattr(self, "scroll_frame") or not self.winfo_exists():
            return
        self._loading = False

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not data:
            empty_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            empty_frame.pack(fill="both", expand=True, pady=40)
            ctk.CTkLabel(
                empty_frame,
                text="📭 No data available",
                font=ctk.CTkFont(size=14),
                text_color="gray",
            ).pack()
            ctk.CTkLabel(
                empty_frame,
                text="Data will appear here once records are added.",
                font=ctk.CTkFont(size=12),
                text_color="gray",
            ).pack(pady=(5, 0))
            return

        for row_idx, row_data in enumerate(data):
            bg_color = ("gray95", "gray17") if row_idx % 2 == 0 else ("gray90", "gray15")
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color=bg_color, corner_radius=4)
            row_frame.pack(fill="x", pady=1)

            # Make row clickable
            if self.on_row_click:
                row_frame.bind("<Button-1>", lambda e, r=row_data: self.on_row_click(r))

            for col_idx, val in enumerate(row_data):
                row_frame.grid_columnconfigure(col_idx, weight=1)
                lbl = ctk.CTkLabel(row_frame, text=str(val), anchor="w")
                lbl.grid(row=0, column=col_idx, sticky="w", padx=10, pady=6)

                if self.on_row_click:
                    lbl.bind("<Button-1>", lambda e, r=row_data: self.on_row_click(r))
