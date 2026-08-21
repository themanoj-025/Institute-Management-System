import customtkinter as ctk

from services.result_service import ResultService
from utils.async_loader import AsyncLoader


class ViewResult(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, *args, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", *args, **kwargs)
        self.tm = tm
        self.result_service = ResultService(db_session)
        self.app_state = app_state

        ctk.CTkLabel(self, text="My Results", font=self.tm.header_font).pack(pady=20, anchor="w")

        # Summary stats
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)

        cards = [
            ("Current SGPA", "—", self.tm.accent_color),
            ("Subjects Passed", "—", self.tm.success_color),
            ("Exams Attempted", "—", self.tm.info_color),
        ]
        self._stat_labels = {}
        for i, (title, val, color) in enumerate(cards):
            f = ctk.CTkFrame(stats_frame, corner_radius=8, border_width=1, border_color=color)
            f.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=12), text_color="gray").pack(
                pady=(10, 0)
            )
            lbl = ctk.CTkLabel(
                f, text=val, font=ctk.CTkFont(size=22, weight="bold"), text_color=color
            )
            lbl.pack(pady=(0, 10))
            self._stat_labels[title] = lbl

        # Exam results breakdown
        self.res_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.res_frame.pack(fill="both", expand=True, pady=20)

        ctk.CTkLabel(
            self.res_frame,
            text="📊 Exam Results Breakdown",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(15, 5), padx=10, anchor="w")

        self._results_content = ctk.CTkFrame(self.res_frame, fg_color="transparent")
        self._results_content.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(
            self._results_content,
            text="Loading results...",
            text_color="gray",
        ).pack(pady=20)

        # Auto-load
        self.after(300, self._load_results)

    def _load_results(self) -> None:
        student_id = self.app_state.current_user.get("profile_id")
        if not student_id:
            ctk.CTkLabel(
                self._results_content,
                text="Student profile not found.",
                text_color="gray",
            ).pack(pady=20)
            return

        AsyncLoader.run(
            self,
            lambda: self.result_service.get_student_results(student_id),
            self._render_results,
        )

    def _render_results(self, results) -> None:
        for w in self._results_content.winfo_children():
            w.destroy()

        if not results:
            self._stat_labels["Current SGPA"].configure(text="—")
            self._stat_labels["Subjects Passed"].configure(text="0")
            self._stat_labels["Exams Attempted"].configure(text="0")
            ctk.CTkLabel(
                self._results_content,
                text="No exam results found for your account.",
                text_color="gray",
            ).pack(pady=20)
            return

        # Calculate stats
        passed = [r for r in results if r["grade"] != "F"]
        failed = [r for r in results if r["grade"] == "F"]
        total_marks = sum(r["marks"] for r in results)
        total_max = sum(r["total"] for r in results)
        overall_pct = round((total_marks / total_max) * 100, 1) if total_max > 0 else 0

        # Calculate SGPA (simplified: average of percentages divided by 10)
        avg_pct = sum(r["pct"] for r in results) / len(results) if results else 0
        sgpa = round(avg_pct / 10, 2)

        self._stat_labels["Current SGPA"].configure(text=str(sgpa))
        self._stat_labels["Subjects Passed"].configure(text=str(len(passed)))
        self._stat_labels["Exams Attempted"].configure(text=str(len(results)))

        # Overall summary bar
        summary_bar = ctk.CTkFrame(
            self._results_content,
            corner_radius=8,
            border_width=1,
            border_color=self.tm.accent_color,
        )
        summary_bar.pack(fill="x", pady=(0, 15))

        pct_color = self.tm.success_color if overall_pct >= 40 else self.tm.danger_color
        ctk.CTkLabel(
            summary_bar,
            text=f"📈 Overall: {overall_pct}% ({total_marks}/{total_max}) — "
            f"{len(passed)} Passed, {len(failed)} Failed  |  SGPA: {sgpa}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=pct_color,
        ).pack(pady=10, padx=15)

        # Table header
        header = ctk.CTkFrame(self._results_content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        cols = ["Subject", "Exam Type", "Marks", "Total", "%", "Grade"]
        widths = [160, 110, 70, 70, 60, 60]
        for i, (h, w) in enumerate(zip(cols, widths)):
            ctk.CTkLabel(
                header,
                text=h,
                font=ctk.CTkFont(weight="bold", size=11),
                width=w,
                anchor="w",
            ).pack(side="left", padx=5)

        # Results rows grouped by exam type
        exam_groups = {}
        for r in results:
            exam_groups.setdefault(r["exam_type"], []).append(r)

        for exam_type, exams in exam_groups.items():
            # Exam type separator
            ctk.CTkLabel(
                self._results_content,
                text=f"▸ {exam_type}",
                font=ctk.CTkFont(weight="bold", size=12, underline=True),
            ).pack(anchor="w", padx=5, pady=(10, 2))

            for idx, r in enumerate(exams):
                bg = ("gray95", "gray17") if idx % 2 == 0 else ("gray90", "gray15")
                row = ctk.CTkFrame(self._results_content, fg_color=bg, corner_radius=4)
                row.pack(fill="x", pady=1)

                grade_color = (
                    self.tm.success_color if r["grade"] not in ("F",) else self.tm.danger_color
                )
                pct_color = self.tm.success_color if r["pct"] >= 40 else self.tm.danger_color

                cells = [
                    (r["subject"], 160),
                    (r["exam_type"], 110),
                    (str(r["marks"]), 70),
                    (str(r["total"]), 70),
                    (f"{r['pct']}%", 60),
                    (r["grade"], 60),
                ]
                for i, (val, w) in enumerate(cells):
                    color = grade_color if i == 5 else (pct_color if i == 4 else None)
                    ctk.CTkLabel(
                        row,
                        text=val,
                        width=w,
                        anchor="w",
                        font=ctk.CTkFont(size=12),
                        text_color=color,
                    ).pack(side="left", padx=5, pady=4)
