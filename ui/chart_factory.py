import time

import customtkinter as ctk
from tkinter import TclError
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class ChartFactory:
    COLORS = [
        "#89b4fa",
        "#a6e3a1",
        "#fab387",
        "#f38ba8",
        "#cba6f7",
        "#94e2d5",
        "#f9e2af",
    ]
    BG_DARK = "#1e1e2e"
    BG_LIGHT = "#eff1f5"
    TEXT_DARK = "#cdd6f4"
    TEXT_LIGHT = "#4c4f69"

    _cache: dict = {}
    CACHE_TTL = 300  # 5 minutes

    @classmethod
    def get_cached(cls, key: str) -> None:
        if key in cls._cache:
            data, timestamp = cls._cache[key]
            if time.time() - timestamp < cls.CACHE_TTL:
                return data
        return None

    @classmethod
    def set_cached(cls, key: str, data) -> None:
        cls._cache[key] = (data, time.time())

    @classmethod
    def create_figure(cls, figsize=(6, 3.5)) -> tuple[Figure, plt.Axes]:
        appearance = ctk.get_appearance_mode().lower()
        bg = cls.BG_DARK if appearance == "dark" else cls.BG_LIGHT
        text_color = cls.TEXT_DARK if appearance == "dark" else cls.TEXT_LIGHT

        plt.rcParams.update(
            {
                "text.color": text_color,
                "axes.labelcolor": text_color,
                "xtick.color": text_color,
                "ytick.color": text_color,
                "figure.facecolor": bg,
                "axes.facecolor": bg,
                "font.family": "sans-serif",
                "font.sans-serif": ["Inter", "DejaVu Sans", "Arial"],
            }
        )

        fig = Figure(figsize=figsize, dpi=100)
        fig.patch.set_facecolor(bg)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        # Remove top/right spines
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(text_color)
        ax.spines["bottom"].set_color(text_color)

        # Horizontal dashed grid
        ax.grid(axis="y", linestyle="--", alpha=0.15)

        return fig, ax

    @classmethod
    def bar(cls, ax, labels, values, title, colors=None, horizontal=False) -> None:
        if not colors:
            colors = cls.COLORS
        if horizontal:
            bars = ax.barh(labels, values, color=colors[: len(labels)], height=0.6)
            ax.bar_label(bars, fmt="%.0f", padding=4)
        else:
            bars = ax.bar(labels, values, color=colors[: len(labels)], width=0.5)
            ax.bar_label(bars, fmt="%.0f", padding=4)
        ax.set_title(title, pad=15, weight="bold")

    @classmethod
    def line(cls, ax, x, y_dict: dict, title, smooth=True) -> None:
        colors = cls.COLORS
        for idx, (label, y) in enumerate(y_dict.items()):
            color = colors[idx % len(colors)]
            if smooth and len(x) > 3:
                try:
                    from scipy.interpolate import make_interp_spline

                    x_indices = np.arange(len(x))
                    x_new = np.linspace(x_indices.min(), x_indices.max(), 300)
                    spl = make_interp_spline(x_indices, y, k=3)
                    y_smooth = spl(x_new)
                    ax.plot(x_new, y_smooth, label=label, color=color, linewidth=2)
                    ax.set_xticks(x_indices)
                    ax.set_xticklabels(x)
                except (ValueError, TypeError):
                    ax.plot(x, y, marker="o", label=label, color=color, linewidth=2)
            else:
                ax.plot(x, y, marker="o", label=label, color=color, linewidth=2)

        ax.set_title(title, pad=15, weight="bold")
        ax.legend(frameon=False)

    @classmethod
    def pie(cls, ax, labels, values, title, donut=False) -> None:
        colors = cls.COLORS
        wedge_props = {"edgecolor": "none"}
        if donut:
            wedge_props["width"] = 0.4

        ax.pie(
            values,
            labels=labels,
            colors=colors[: len(labels)],
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops=wedge_props,
            textprops={"weight": "bold"},
        )

        ax.set_title(title, pad=15, weight="bold")

    @classmethod
    def radar(cls, ax, categories, values_dict: dict, title) -> None:
        # ax must have polar=True projection
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        colors = cls.COLORS
        for idx, (label, values) in enumerate(values_dict.items()):
            color = colors[idx % len(colors)]
            val_list = list(values)
            val_list += val_list[:1]
            ax.plot(angles, val_list, color=color, linewidth=2, label=label)
            ax.fill(angles, val_list, color=color, alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_title(title, pad=20, weight="bold")
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), frameon=False)

    @classmethod
    def heatmap(cls, fig, ax, df, title) -> None:
        sns.heatmap(
            df,
            annot=True,
            fmt=".0f",
            cmap="Blues",
            ax=ax,
            cbar=False,
            annot_kws={"weight": "bold", "size": 10},
        )
        ax.set_title(title, pad=15, weight="bold")

    @classmethod
    def scatter(cls, ax, x, y, colors, labels, title) -> None:
        sc = ax.scatter(x, y, c=colors, s=50, alpha=0.8, edgecolors="none")
        ax.set_title(title, pad=15, weight="bold")

        # Tooltip on hover using mplcursors if installed
        try:
            import mplcursors

            cursor = mplcursors.cursor(sc, hover=True)

            @cursor.connect("add")
            def on_add(sel) -> None:
                sel.annotation.set_text(labels[sel.index])

        except (ValueError, TypeError, AttributeError):
            pass

    @classmethod
    def boxplot(cls, ax, data_dict: dict, title) -> None:
        labels = list(data_dict.keys())
        data = list(data_dict.values())

        box = ax.boxplot(data, patch_artist=True, labels=labels)

        colors = cls.COLORS
        for patch, color in zip(box["boxes"], colors[: len(labels)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        for median in box["medians"]:
            median.set_color("#1e1e2e")
            median.set_linewidth(2)

        ax.set_title(title, pad=15, weight="bold")

    @classmethod
    def embed(cls, fig, parent: ctk.CTkFrame) -> FigureCanvasTkAgg:
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # Auto-tight on configuration transitions
        def on_resize(event) -> None:
            try:
                fig.tight_layout()
                canvas.draw_idle()
            except (TclError, RuntimeError, OSError):
                pass

        parent.bind("<Configure>", on_resize)
        return canvas
