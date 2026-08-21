"""Admin analytics dashboard — real charts from the AnalyticsEngine."""

import customtkinter as ctk

from analytics.engine import AnalyticsEngine
from services.analytics_service import AnalyticsService
from ui.chart_factory import ChartFactory
from utils.async_loader import AsyncLoader


class AnalyticsDashboard(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.db_session = db_session
        self.engine = AnalyticsEngine(db_session)
        self.analytics_svc = AnalyticsService(db_session)
        self._loading = False

        # ── Header row with title + Refresh button ──
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", pady=(20, 0))

        ctk.CTkLabel(header_row, text="Advanced Analytics", font=self.tm.header_font).pack(
            side="left"
        )

        self.refresh_btn = ctk.CTkButton(
            header_row,
            text="🔄 Refresh Data",
            width=130,
            height=32,
            fg_color=self.tm.accent_color,
            command=self._manual_refresh,
        )
        self.refresh_btn.pack(side="right", padx=(10, 0))

        ctk.CTkLabel(
            self,
            text="Deep dive into student performance, attendance trends, and financial reports.",
            font=self.tm.main_font,
            text_color="gray",
        ).pack(anchor="w", pady=(2, 0))

        # ── Top metrics row (loaded async) ──
        self.metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.metrics_frame.pack(fill="x", pady=15)

        self._metric_labels = {}
        metric_titles = [
            ("attendance", "📈 Avg Attendance", self.tm.success_color),
            ("performance", "🎯 Avg Marks", self.tm.accent_color),
            ("placements", "💼 Total Placements", self.tm.info_color),
            ("collection", "💰 Collection Rate", self.tm.warning_color),
        ]
        for i, (key, title, color) in enumerate(metric_titles):
            card = ctk.CTkFrame(
                self.metrics_frame, corner_radius=8, border_width=1, border_color=color
            )
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            self.metrics_frame.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color="gray").pack(
                pady=(10, 0)
            )
            val_lbl = ctk.CTkLabel(
                card,
                text="—",
                font=ctk.CTkFont(size=22, weight="bold"),
                text_color=color,
            )
            val_lbl.pack(pady=(0, 10))
            self._metric_labels[key] = val_lbl

        # ── Charts grid (4 charts in 2x2) ──
        charts_grid = ctk.CTkFrame(self, fg_color="transparent")
        charts_grid.pack(fill="both", expand=True, pady=10)
        charts_grid.grid_rowconfigure(0, weight=1)
        charts_grid.grid_rowconfigure(1, weight=1)
        charts_grid.grid_columnconfigure(0, weight=1)
        charts_grid.grid_columnconfigure(1, weight=1)

        # Chart 1 — Attendance Trend (line)
        self.chart1_frame = ctk.CTkFrame(charts_grid, corner_radius=10)
        self.chart1_frame.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(
            self.chart1_frame,
            text="📈 Attendance Trends (6 months)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(10, 2))
        self.chart1_body = ctk.CTkFrame(self.chart1_frame, fg_color="transparent")
        self.chart1_body.pack(fill="both", expand=True, padx=5, pady=2)

        # Chart 2 — Course Performance (grouped bar)
        self.chart2_frame = ctk.CTkFrame(charts_grid, corner_radius=10)
        self.chart2_frame.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(
            self.chart2_frame,
            text="📊 Course Performance",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(10, 2))
        self.chart2_body = ctk.CTkFrame(self.chart2_frame, fg_color="transparent")
        self.chart2_body.pack(fill="both", expand=True, padx=5, pady=2)

        # Chart 3 — Fee Collection (donut pie)
        self.chart3_frame = ctk.CTkFrame(charts_grid, corner_radius=10)
        self.chart3_frame.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(
            self.chart3_frame,
            text="💰 Fee Collection Status",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(10, 2))
        self.chart3_body = ctk.CTkFrame(self.chart3_frame, fg_color="transparent")
        self.chart3_body.pack(fill="both", expand=True, padx=5, pady=2)

        # Chart 4 — Top Placement Companies (horizontal bar)
        self.chart4_frame = ctk.CTkFrame(charts_grid, corner_radius=10)
        self.chart4_frame.grid(row=1, column=1, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(
            self.chart4_frame,
            text="🎓 Top Placement Companies",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=(10, 2))
        self.chart4_body = ctk.CTkFrame(self.chart4_frame, fg_color="transparent")
        self.chart4_body.pack(fill="both", expand=True, padx=5, pady=2)

        # Load all data
        self._load_all()

    def _manual_refresh(self) -> None:
        """Refresh button handler — reloads all charts while disabling the button."""
        if self._loading:
            return
        self._loading = True
        self.refresh_btn.configure(text="⏳ Refreshing...", state="disabled")
        AsyncLoader.run(self, self._fetch_all, self._render_all, on_error=self._on_refresh_error)

    def _load_all(self) -> None:
        """Load all analytics data in the background (initial load)."""
        self._loading = True
        AsyncLoader.run(self, self._fetch_all, self._render_all, on_error=self._on_refresh_error)

    def _on_refresh_error(self, error) -> None:
        """Handle errors during data fetch — re-enable the refresh button."""
        self._loading = False
        self.refresh_btn.configure(text="🔄 Refresh Data", state="normal")
        try:
            from ui.toast import ToastManager

            ToastManager.show(
                self.winfo_toplevel(),
                f"Failed to refresh analytics: {error}",
                "error",
            )
        except Exception:
            pass

    def _fetch_all(self) -> None:
        """Fetch summary + course performance in one background pass."""
        summary = self.engine.full_summary()
        summary["course_performance"] = self.analytics_svc.get_course_performance_breakdown()
        return summary

    def _render_all(self, data) -> None:
        # Re-enable refresh button
        self.refresh_btn.configure(text="🔄 Refresh Data", state="normal")
        self._loading = False

        summary = data
        att = summary.get("attendance", {})
        fees = summary.get("fees", {})
        perf = summary.get("performance", {})
        placements = summary.get("placements", {})
        att_trend = summary.get("attendance_trend", [])
        course_perf = summary.get("course_performance", [])

        # ── Update metric cards ──
        self._metric_labels["attendance"].configure(text=f"{att.get('present_rate', 0)}%")
        self._metric_labels["performance"].configure(text=f"{perf.get('average_percentage', 0)}%")
        self._metric_labels["placements"].configure(text=str(placements.get("total_placements", 0)))
        self._metric_labels["collection"].configure(text=f"{fees.get('collection_rate', 0)}%")

        # ── Chart 1: Attendance Trend (line) ──
        self._render_attendance_trend(att_trend, att)

        # ── Chart 2: Course Performance (bar) ──
        self._render_course_performance(course_perf)

        # ── Chart 3: Fee Collection (donut) ──
        self._render_fee_pie(fees)

        # ── Chart 4: Top Placement Companies (horizontal bar) ──
        self._render_placements(placements)

    # ── Individual chart renderers ──

    def _render_attendance_trend(self, trend_data, att_summary) -> None:
        for w in self.chart1_body.winfo_children():
            w.destroy()

        fig, ax = ChartFactory.create_figure((5.5, 2.8))

        if trend_data:
            months = [t["month"] for t in trend_data]
            rates = [t["rate"] for t in trend_data]
            ChartFactory.line(ax, months, {"Attendance Rate": rates}, "")
        else:
            daily = att_summary.get("daily_breakdown", [])
            if daily:
                dates = [d["date"] for d in daily[-14:]]
                rates = [
                    (d["present"] / d["total"]) * 100 if d["total"] > 0 else 0 for d in daily[-14:]
                ]
                ChartFactory.line(ax, dates, {"Attendance Rate": rates}, "")
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No attendance data available",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=11,
                    color="gray",
                )
                ax.set_title("No Trend Data", pad=15, weight="bold")

        ChartFactory.embed(fig, self.chart1_body)

    def _render_course_performance(self, course_perf) -> None:
        """Render grouped bar chart using pre-computed data from AnalyticsService."""
        for w in self.chart2_body.winfo_children():
            w.destroy()

        fig, ax = ChartFactory.create_figure((5.5, 2.8))

        if not course_perf:
            ax.text(
                0.5,
                0.5,
                "No course performance data",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=11,
                color="gray",
            )
            ChartFactory.embed(fig, self.chart2_body)
            return

        import numpy as np

        names = [c["course_name"][:10] for c in course_perf]
        att_rates = [c["avg_attendance_rate"] for c in course_perf]
        marks_avg = [c["avg_marks_pct"] for c in course_perf]

        x = np.arange(len(names))
        width = 0.35

        bars1 = ax.bar(
            x - width / 2,
            att_rates,
            width,
            label="Attendance %",
            color=ChartFactory.COLORS[0],
        )
        bars2 = ax.bar(
            x + width / 2,
            marks_avg,
            width,
            label="Marks %",
            color=ChartFactory.COLORS[1],
        )

        ax.bar_label(bars1, fmt="%.0f", fontsize=8, padding=2)
        ax.bar_label(bars2, fmt="%.0f", fontsize=8, padding=2)
        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=8)
        ax.legend(frameon=False, fontsize=9)

        ChartFactory.embed(fig, self.chart2_body)

    def _render_fee_pie(self, fees) -> None:
        for w in self.chart3_body.winfo_children():
            w.destroy()

        fig, ax = ChartFactory.create_figure((5.5, 2.8))

        paid = fees.get("paid_count", 0)
        unpaid = fees.get("unpaid_count", 0)
        total = fees.get("total_records", 0)
        partial = total - paid - unpaid

        if total > 0:
            labels = ["Paid", "Partial", "Unpaid"]
            values = [paid, max(partial, 0), unpaid]
            non_zero = [(lb, v) for lb, v in zip(labels, values) if v > 0]
            if non_zero:
                ChartFactory.pie(
                    ax,
                    [n[0] for n in non_zero],
                    [n[1] for n in non_zero],
                    "",
                    donut=True,
                )
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No fee data",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=11,
                    color="gray",
                )
        else:
            ax.text(
                0.5,
                0.5,
                "No fee records",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=11,
                color="gray",
            )

        ChartFactory.embed(fig, self.chart3_body)

    def _render_placements(self, placements) -> None:
        for w in self.chart4_body.winfo_children():
            w.destroy()

        fig, ax = ChartFactory.create_figure((5.5, 2.8))

        top_companies = placements.get("top_companies", [])

        if top_companies:
            companies = top_companies[:8]
            names = [c["name"][:15] for c in companies]
            counts = [c["placements"] for c in companies]
            names.reverse()
            counts.reverse()
            ChartFactory.bar(ax, names, counts, "", horizontal=True)
        else:
            total = placements.get("total_placements", 0)
            avg_pkg = placements.get("average_package_lpa", 0)
            max_pkg = placements.get("max_package_lpa", 0)
            info_text = f"Total: {total} | Avg: ₹{avg_pkg}L | Max: ₹{max_pkg}L"
            ax.text(
                0.5,
                0.6,
                info_text,
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=10,
                color="gray",
            )
            ax.text(
                0.5,
                0.4,
                "No company data for chart",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=10,
                color="gray",
                style="italic",
            )

        ChartFactory.embed(fig, self.chart4_body)
