import customtkinter as ctk

from landing.login_dialog import LoginDialog


class LandingPage(ctk.CTkFrame):
    def __init__(self, master, tm, app_state, db_session, show_main_app_cb, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.tm = tm
        self.app_state = app_state
        self.db_session = db_session
        self.show_main_app_cb = show_main_app_cb

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        self._build_hero_section()
        self._build_courses_section()
        self._build_login_section()
        self._build_contact_section()

    def _build_hero_section(self) -> None:
        hero = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hero.pack(fill="x", pady=40, padx=20)

        ctk.CTkLabel(
            hero,
            text="Binary Brain Institute of Technology",
            font=ctk.CTkFont(size=40, weight="bold"),
        ).pack(pady=10)
        ctk.CTkLabel(
            hero,
            text="Shaping the Future of Tech Education Since 2015",
            font=self.tm.main_font,
            text_color="gray",
        ).pack()

        stats_frame = ctk.CTkFrame(hero, fg_color="transparent")
        stats_frame.pack(pady=30)

        from ui.animations import CounterAnimation

        stats = [
            ("Students", 5000, "+"),
            ("Faculty", 50, "+"),
            ("Courses", 12, ""),
            ("Placement Rate", 98, "%"),
        ]
        for i, (title, val, sfx) in enumerate(stats):
            f = ctk.CTkFrame(stats_frame, corner_radius=10)
            f.grid(row=0, column=i, padx=10)
            lbl = ctk.CTkLabel(
                f,
                text="0",
                font=ctk.CTkFont(size=30, weight="bold"),
                text_color=self.tm.accent_color,
            )
            lbl.pack(padx=20, pady=(10, 0))
            ctk.CTkLabel(f, text=title, font=self.tm.small_font).pack(padx=20, pady=(0, 10))
            # Stagger the counter animations to avoid lag
            self.after(
                i * 200,
                lambda label=lbl, v=val, s=sfx: CounterAnimation.animate(
                    label, v, duration_ms=1200, suffix=s
                ),
            )

    def _build_courses_section(self) -> None:
        from config.constants import AVAILABLE_COURSES

        frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        frame.pack(fill="x", pady=40, padx=20)
        ctk.CTkLabel(frame, text="Our Courses", font=self.tm.header_font).pack(pady=20)

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack()

        for i, course in enumerate(AVAILABLE_COURSES):
            row = i // 3
            col = i % 3
            c_card = ctk.CTkFrame(grid, corner_radius=10, border_width=1, border_color="gray50")
            c_card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            ctk.CTkLabel(
                c_card, text=course["name"], font=ctk.CTkFont(size=16, weight="bold")
            ).pack(pady=10, padx=10)
            ctk.CTkLabel(
                c_card,
                text=f"Duration: {course['duration']} Months | Fee: ₹{course['fee']}",
            ).pack()

            btn_frame = ctk.CTkFrame(c_card, fg_color="transparent")
            btn_frame.pack(pady=10)

            ctk.CTkButton(
                btn_frame,
                text="View Syllabus",
                width=100,
                fg_color="gray",
                command=lambda c=course: self._show_syllabus(c),
            ).pack(side="left", padx=5)
            ctk.CTkButton(
                btn_frame,
                text="Apply Now",
                width=100,
                command=lambda c=course: self._apply_now(c),
            ).pack(side="left", padx=5)

    def _show_syllabus(self, course) -> None:
        """Display a detailed syllabus dialog for the selected course."""
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title(f"{course['code']} — {course['name']}")
        dialog.geometry("800x700")
        dialog.minsize(600, 500)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        pw = self.winfo_toplevel().winfo_width()
        ph = self.winfo_toplevel().winfo_height()
        px = self.winfo_toplevel().winfo_x()
        py = self.winfo_toplevel().winfo_y()
        dw, dh = 800, 700
        dialog.geometry(f"{dw}x{dh}+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

        main_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Header ---
        header = ctk.CTkFrame(main_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            header,
            text=f"{course['name']}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.tm.accent_color,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=f"Course Code: {course['code']}  |  Duration: {course['duration']} Months  |  Fee: ₹{course['fee']:,}",
            font=self.tm.main_font,
            text_color="gray",
        ).pack(anchor="w", pady=(2, 0))

        # --- Description ---
        desc_frame = ctk.CTkFrame(main_frame, corner_radius=8)
        desc_frame.pack(fill="x", pady=8)
        ctk.CTkLabel(
            desc_frame,
            text="📖 Course Overview",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(12, 5))
        desc = course.get("description", "")
        ctk.CTkLabel(
            desc_frame,
            text=desc,
            wraplength=700,
            justify="left",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=15, pady=(0, 12))

        # --- Prerequisites ---
        prereqs = course.get("prerequisites", [])
        if prereqs:
            prereq_frame = ctk.CTkFrame(main_frame, corner_radius=8)
            prereq_frame.pack(fill="x", pady=8)
            ctk.CTkLabel(
                prereq_frame,
                text="🎯 Prerequisites",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(anchor="w", padx=15, pady=(12, 5))
            for p in prereqs:
                ctk.CTkLabel(
                    prereq_frame,
                    text=f"  •  {p}",
                    wraplength=680,
                    justify="left",
                    font=ctk.CTkFont(size=13),
                ).pack(anchor="w", padx=25, pady=1)
            ctk.CTkLabel(prereq_frame, text="", height=6).pack()

        # --- Learning Outcomes ---
        outcomes = course.get("learning_outcomes", [])
        if outcomes:
            outcome_frame = ctk.CTkFrame(main_frame, corner_radius=8)
            outcome_frame.pack(fill="x", pady=8)
            ctk.CTkLabel(
                outcome_frame,
                text="🏆 What You Will Learn",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(anchor="w", padx=15, pady=(12, 5))
            for o in outcomes:
                ctk.CTkLabel(
                    outcome_frame,
                    text=f"  ✅  {o}",
                    wraplength=680,
                    justify="left",
                    font=ctk.CTkFont(size=13),
                ).pack(anchor="w", padx=25, pady=1)
            ctk.CTkLabel(outcome_frame, text="", height=6).pack()

        # --- Career Opportunities ---
        careers = course.get("career_opportunities", [])
        if careers:
            career_frame = ctk.CTkFrame(main_frame, corner_radius=8)
            career_frame.pack(fill="x", pady=8)
            ctk.CTkLabel(
                career_frame,
                text="💼 Career Opportunities",
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(anchor="w", padx=15, pady=(12, 5))
            for c in careers:
                ctk.CTkLabel(
                    career_frame,
                    text=f"  ➤  {c}",
                    wraplength=680,
                    justify="left",
                    font=ctk.CTkFont(size=13),
                ).pack(anchor="w", padx=25, pady=1)
            ctk.CTkLabel(career_frame, text="", height=6).pack()

        # --- Modules ---
        modules = course.get("modules", [])
        if modules:
            mod_header = ctk.CTkFrame(main_frame, fg_color="transparent")
            mod_header.pack(fill="x", pady=(15, 8))
            ctk.CTkLabel(
                mod_header,
                text="📚 Course Syllabus — Module Breakdown",
                font=ctk.CTkFont(size=18, weight="bold"),
            ).pack(anchor="w")

            for idx, mod in enumerate(modules):
                mf = ctk.CTkFrame(
                    main_frame, corner_radius=8, border_width=1, border_color="gray30"
                )
                mf.pack(fill="x", pady=6)

                # Module title bar
                title_bar = ctk.CTkFrame(mf, fg_color="#2d5a27", height=32, corner_radius=8)
                title_bar.pack(fill="x")
                title_text = mod.get("title", f"Module {idx + 1}")
                dur = mod.get("duration_weeks", 0)
                title_lbl = ctk.CTkLabel(
                    title_bar,
                    text=f"{title_text}  ({dur} week{'s' if dur != 1 else ''})",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white",
                )
                title_lbl.pack(padx=15, pady=4, anchor="w")

                # Module topics
                topics = mod.get("topics", [])
                topics_frame = ctk.CTkFrame(mf, fg_color="transparent")
                topics_frame.pack(fill="x", padx=15, pady=10)
                for t in topics:
                    ctk.CTkLabel(
                        topics_frame,
                        text=f"▸  {t}",
                        wraplength=680,
                        justify="left",
                        font=ctk.CTkFont(size=12),
                    ).pack(anchor="w", pady=2)

        # --- Apply button ---
        ctk.CTkButton(
            main_frame,
            text=f"Apply for {course['code']} — ₹{course['fee']:,}",
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=lambda: self._apply_now(course),
        ).pack(pady=20)

        ctk.CTkLabel(main_frame, text="", height=10).pack()

    def _apply_now(self, course) -> None:
        """Open a dialog to submit an enquiry directly for the selected course."""
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title(f"Apply for {course['code']} — {course['name']}")
        dialog.geometry("500x520")
        dialog.minsize(450, 480)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        pw = self.winfo_toplevel().winfo_width()
        ph = self.winfo_toplevel().winfo_height()
        px = self.winfo_toplevel().winfo_x()
        py = self.winfo_toplevel().winfo_y()
        dw, dh = 500, 520
        dialog.geometry(f"{dw}x{dh}+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

        main_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        ctk.CTkLabel(
            main_frame,
            text=f"Apply for {course['name']}",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.tm.accent_color,
        ).pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(
            main_frame,
            text=f"Course: {course['code']}  |  Fee: ₹{course['fee']:,}  |  Duration: {course['duration']} Months",
            font=self.tm.main_font,
            text_color="gray",
        ).pack(anchor="w", pady=(0, 15))

        # Form fields
        form = ctk.CTkFrame(main_frame, fg_color="transparent")
        form.pack(fill="x")

        ctk.CTkLabel(form, text="Full Name *", font=self.tm.main_font).pack(
            anchor="w", pady=(10, 2)
        )
        name_entry = ctk.CTkEntry(form, placeholder_text="Enter your full name", height=38)
        name_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Email Address *", font=self.tm.main_font).pack(
            anchor="w", pady=(10, 2)
        )
        email_entry = ctk.CTkEntry(form, placeholder_text="Enter your email address", height=38)
        email_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Phone Number", font=self.tm.main_font).pack(
            anchor="w", pady=(10, 2)
        )
        phone_entry = ctk.CTkEntry(form, placeholder_text="Enter your phone number", height=38)
        phone_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Message (Optional)", font=self.tm.main_font).pack(
            anchor="w", pady=(10, 2)
        )
        message_text = ctk.CTkTextbox(form, height=80)
        message_text.pack(fill="x", pady=(0, 5))
        message_text.insert(
            "1.0",
            f"I am interested in joining the {course['name']} program. Please send me more details.",
        )

        def submit() -> None:
            name = name_entry.get().strip()
            email = email_entry.get().strip()
            phone = phone_entry.get().strip()
            message = message_text.get("1.0", "end").strip()

            if not name:
                from ui.toast import ToastManager

                ToastManager.show(dialog, "Please enter your name.", "warning")
                return
            if not email:
                from ui.toast import ToastManager

                ToastManager.show(dialog, "Please enter your email address.", "warning")
                return

            from utils.validators import validate_email, validate_phone

            if not validate_email(email):
                from ui.toast import ToastManager

                ToastManager.show(dialog, "Please enter a valid email address.", "error")
                return

            if phone and not validate_phone(phone):
                from ui.toast import ToastManager

                ToastManager.show(
                    dialog,
                    "Please enter a valid 10-digit Indian phone number (starting with 6-9).",
                    "warning",
                )
                return

            try:

                from database.models import Enquiry

                enquiry = Enquiry(
                    name=name,
                    email=email,
                    phone=phone or None,
                    message=message if message else f"Enquiry for {course['code']} course",
                    course_interest=course["code"],
                    is_resolved=False,
                )
                self.db_session.add(enquiry)
                self.db_session.commit()

                from ui.toast import ToastManager

                ToastManager.show(
                    self.winfo_toplevel(),
                    f"✅ Application submitted! Thank you {name}. We'll contact you soon.",
                    "success",
                )
                dialog.destroy()
            except (ValueError, KeyError, OSError) as e:
                self.db_session.rollback()
                from ui.toast import ToastManager

                ToastManager.show(dialog, f"Error submitting: {e!s}", "error")

        # Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color="gray",
            command=dialog.destroy,
            width=120,
            height=40,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_frame,
            text="📩 Submit Application",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=submit,
            width=200,
            height=40,
        ).pack(side="right")

        ctk.CTkLabel(
            main_frame,
            text="* Required fields",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", pady=(10, 0))

    def _build_login_section(self) -> None:
        frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        frame.pack(fill="x", pady=40, padx=20)
        ctk.CTkLabel(frame, text="Portal Login", font=self.tm.header_font).pack(pady=20)

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack()

        roles = [
            ("Admin", "admin", self.tm.danger_color),
            ("Staff", "staff", self.tm.success_color),
            ("Student", "student", self.tm.accent_color),
        ]

        for i, (title, role_val, color) in enumerate(roles):
            btn = ctk.CTkButton(
                grid,
                text=f"{title} Login",
                fg_color=color,
                font=ctk.CTkFont(size=18),
                height=50,
                command=lambda r=role_val: self._open_login(r),
            )
            btn.grid(row=0, column=i, padx=20)

    def _open_login(self, role) -> None:
        LoginDialog(
            self.winfo_toplevel(),
            self.tm,
            role,
            self.db_session,
            self.app_state,
            self.show_main_app_cb,
        )

    def logout(self) -> None:
        """Log out and return to the landing page.

        Calls POST /v1/auth/logout to blacklist the token server-side.
        """
        token = None
        if hasattr(self.app_state, "current_user") and self.app_state.current_user:
            token = self.app_state.current_user.get("access_token")

        if token:
            try:
                from landing.login_dialog import _api_logout

                _api_logout(token)
            except (OSError, ConnectionError, ValueError):
                pass  # Non-blocking — best-effort token blacklisting

        # Clear session state
        self.app_state.current_user = None
        self.app_state.current_route = None

        # Clear desktop UI
        master = self.winfo_toplevel()
        if hasattr(master, "handle_logout"):
            master.handle_logout()
        else:
            # Fallback: clear main window and re-show landing
            for widget in master.winfo_children():
                widget.destroy()
            self.pack(fill="both", expand=True)

    def _build_contact_section(self) -> None:
        frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        frame.pack(fill="x", pady=40, padx=20)
        ctk.CTkLabel(frame, text="Contact Us", font=self.tm.header_font).pack(pady=20)

        # Simplified contact form
        form = ctk.CTkFrame(frame, corner_radius=12)
        form.pack(pady=10)

        self.contact_name = ctk.CTkEntry(form, placeholder_text="Your Name", width=350, height=38)
        self.contact_name.pack(pady=8, padx=25)
        self.contact_email = ctk.CTkEntry(form, placeholder_text="Your Email", width=350, height=38)
        self.contact_email.pack(pady=8, padx=25)

        def submit_enquiry() -> None:
            name = self.contact_name.get().strip()
            email = self.contact_email.get().strip()
            if name and email:
                from utils.validators import validate_email

                if not validate_email(email):
                    from ui.toast import ToastManager

                    ToastManager.show(
                        self.winfo_toplevel(),
                        "Please enter a valid email address.",
                        "error",
                    )
                    return
                try:

                    from database.models import Enquiry

                    enquiry = Enquiry(
                        name=name,
                        email=email,
                        phone=None,
                        message=f"Contact form enquiry from {name} ({email})",
                        course_interest=None,
                        is_resolved=False,
                    )
                    self.db_session.add(enquiry)
                    self.db_session.commit()

                    from ui.toast import ToastManager

                    ToastManager.show(
                        self.winfo_toplevel(),
                        f"Thank you {name}! We will contact you soon. ✅",
                        "success",
                    )
                    self.contact_name.delete(0, "end")
                    self.contact_email.delete(0, "end")
                except (ValueError, KeyError, OSError) as e:
                    self.db_session.rollback()
                    from ui.toast import ToastManager

                    ToastManager.show(
                        self.winfo_toplevel(),
                        f"Error submitting enquiry: {e!s}",
                        "error",
                    )
            else:
                from ui.toast import ToastManager

                ToastManager.show(
                    self.winfo_toplevel(),
                    "Please fill in your name and email.",
                    "warning",
                )

        self.submit_enq_btn = ctk.CTkButton(
            form, text="📩 Submit Enquiry", command=submit_enquiry, width=200, height=40
        )
        self.submit_enq_btn.pack(pady=(15, 20))

        # Contact info
        info_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        info_frame.pack(fill="x", pady=20, padx=20)

        ctk.CTkLabel(
            info_frame,
            text="📍 123 Tech Park, Bangalore, India — 📞 +91 98765 43210 — ✉ info@binarybrain.edu.in",
            font=self.tm.small_font,
            text_color="gray",
        ).pack()
        ctk.CTkLabel(
            info_frame,
            text="© 2025 Binary Brain Institute of Technology. All rights reserved.",
            font=self.tm.small_font,
            text_color="gray",
        ).pack(pady=(5, 10))
