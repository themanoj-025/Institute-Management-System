import customtkinter as ctk


class HoverEffect:
    @staticmethod
    def bind_card(widget: ctk.CTkFrame, normal_color: str, hover_color: str) -> None:
        def on_enter(e) -> None:
            if widget.winfo_exists():
                widget.configure(fg_color=hover_color)

        def on_leave(e) -> None:
            if widget.winfo_exists():
                widget.configure(fg_color=normal_color)

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        # Bind recursively to all child widgets within the frame
        for child in widget.winfo_children():
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)


class CounterAnimation:
    @staticmethod
    def animate(label: ctk.CTkLabel, target: int, duration_ms: int = 1200, prefix="", suffix="") -> None:
        steps = 30
        step_ms = duration_ms // steps

        def tick(current_step) -> None:
            if not label.winfo_exists():
                return
            try:
                val = int(target * (current_step / steps))
                label.configure(text=f"{prefix}{val:,}{suffix}")
                if current_step < steps:
                    label.after(step_ms, lambda: tick(current_step + 1))
                else:
                    label.configure(text=f"{prefix}{target:,}{suffix}")
            except Exception:
                pass

        tick(0)


class SlideTransition:
    @staticmethod
    def fade_in(widget, duration_ms=200) -> None:
        # Color interpolation from #1e1e2e (mocha base) or #eff1f5 (latte base) to surface
        steps = 10
        step_ms = duration_ms // steps

        # Simple color blend helper
        def hex_to_rgb(hex_str) -> None:
            hex_str = hex_str.lstrip("#")
            return tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb) -> None:
            return "#{:02x}{:02x}{:02x}".format(*rgb)

        appearance = ctk.get_appearance_mode().lower()
        bg_hex = "#1e1e2e" if appearance == "dark" else "#eff1f5"
        fg_hex = "#181825" if appearance == "dark" else "#ffffff"

        try:
            bg_rgb = hex_to_rgb(bg_hex)
            fg_rgb = hex_to_rgb(fg_hex)
        except Exception:
            # Fallback
            return

        def blend(step) -> None:
            if not widget.winfo_exists():
                return
            ratio = step / steps
            curr_rgb = tuple(int(bg_rgb[i] + (fg_rgb[i] - bg_rgb[i]) * ratio) for i in range(3))
            widget.configure(fg_color=rgb_to_hex(curr_rgb))
            if step < steps:
                widget.after(step_ms, blend, step + 1)

        blend(0)
