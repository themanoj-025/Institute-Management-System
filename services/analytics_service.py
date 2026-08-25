"""
Analytics service — provides KPI data, at-risk student lists, and
attendance predictions by delegating to the ML module.

This is the shared business-logic layer used by both the desktop UI
and the API. It replaces the previous inline numpy.polyfit
implementation and memory-heavy sum aggregations with the ML service
layer (``ml/service.py``).

Advanced KPIs include:
- Course-wise performance breakdown
- Attendance anomaly detection
- Fee collection forecast
- Retention risk signals
- Comparative analytics (course vs course)
"""

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import case as sql_case
from sqlalchemy import func
from sqlalchemy.orm import Session

from ml.service import MLService
from utils.time import utc_now

logger = logging.getLogger("analytics")


class AnalyticsService:
    """Provides analytics and ML-powered predictions.

    All methods delegate to ``MLService`` for ML operations and use
    SQL aggregate functions for database queries (no loading entire
    tables into Python memory).
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._ml = MLService()

    # ── Core KPIs ──────────────────────────────────────────────────

    def get_dashboard_kpis(self) -> dict[str, Any]:
        """Return key performance indicators for the admin dashboard.

        Uses SQL aggregates (via MLService) instead of loading entire
        tables into Python memory.
        """
        return self._ml.get_dashboard_kpis(self.db)

    def get_advanced_kpis(self) -> dict[str, Any]:
        """Return advanced KPIs with ML-driven insights.

        Combines course-wise performance, attendance anomaly detection,
        fee collection forecasts, and retention signals into a single
        response for the analytics dashboard.
        """
        return {
            "course_performance": self.get_course_performance_breakdown(),
            "attendance_anomalies": self.get_attendance_anomalies(),
            "fee_forecast": self._compute_fee_forecast(),
            "retention_signals": self.get_retention_risk_signals(),
            "comparative": self.get_comparative_analytics(),
        }

    def predict_attendance_trend(self, student_id: int) -> dict[str, Any]:
        """Predict the attendance trend for a student over the next 4 weeks.

        Delegates to ``MLService.predict_attendance_trend()`` which uses
        linear regression with proper data preparation.
        """
        return self._ml.predict_attendance_trend(self.db, student_id)

    def get_at_risk_students(self, threshold: float = 0.5, top_n: int = 20) -> list[dict[str, Any]]:
        """Return the top-N most at-risk students.

        Uses the XGBoost risk model if available, falling back to a
        heuristic threshold-based assessment if the model hasn't been
        trained yet.

        Parameters
        ----------
        threshold : float
            Minimum risk probability (default 0.5).
        top_n : int
            Maximum number of students (default 20).

        Returns
        -------
        list[dict]
            Each entry contains student info, risk_score, risk_level,
            and explanations (top-3 contributing factors).
        """
        return self._ml.get_at_risk_students(self.db, threshold=threshold, top_n=top_n)

    def predict_student_risk(self, student_id: int) -> dict[str, Any] | None:
        """Predict risk for a single student with full SHAP explanation.

        Returns a dict with risk_score, risk_level, and explanations
        (top-3 contributing factors with direction and values).
        """
        return self._ml.predict_student_risk(self.db, student_id)

    def train_model(self, force: bool = False) -> bool:
        """Train or retrain the ML risk prediction model.

        Parameters
        ----------
        force : bool
            If True, retrain even if a model already exists.

        Returns
        -------
        bool
            True if training succeeded.
        """
        trained, metrics = self._ml.train(self.db, force=force)
        if trained:
            logger.info("Model training complete. Metrics: %s", metrics)
        return trained

    # ── Advanced KPIs ──────────────────────────────────────────────

    def get_course_performance_breakdown(self) -> list[dict[str, Any]]:
        """Compute per-course performance metrics.

        For each course, returns average attendance rate, average marks,
        fee collection rate, and placement rate.

        Returns
        -------
        list[dict]
            Each entry: course_id, course_name, avg_attendance, avg_marks,
            fee_collection_rate, placement_rate, student_count.
        """
        from database.models import Attendance, Course, Fee, Placement, Result, Student

        courses = self.db.query(Course).all()
        results = []

        for course in courses:
            # Student count
            student_count = (
                self.db.query(func.count(Student.id))
                .filter(Student.course_id == course.id)
                .scalar()
                or 0
            )
            if student_count == 0:
                continue

            student_ids = [
                s[0] for s in self.db.query(Student.id).filter(Student.course_id == course.id).all()
            ]

            # Average attendance rate (last 4 weeks)
            cutoff = date.today() - timedelta(days=28)
            att_data = (
                self.db.query(
                    func.avg(
                        sql_case(
                            (Attendance.status.in_(["present", "late"]), 1.0),
                            else_=0.0,
                        )
                    )
                )
                .filter(
                    Attendance.student_id.in_(student_ids),
                    Attendance.date >= cutoff,
                )
                .scalar()
            )
            avg_attendance = round(float(att_data) * 100, 1) if att_data else 0.0

            # Average marks
            marks_data = (
                self.db.query(func.avg(Result.marks_obtained / Result.total_marks * 100))
                .filter(
                    Result.student_id.in_(student_ids),
                    Result.is_deleted == False,
                    Result.total_marks > 0,
                )
                .scalar()
            )
            avg_marks = round(float(marks_data), 1) if marks_data else 0.0

            # Fee collection rate
            fee_data = (
                self.db.query(
                    func.coalesce(func.sum(Fee.paid_amount), 0),
                    func.coalesce(func.sum(Fee.total_amount), 0),
                )
                .filter(
                    Fee.student_id.in_(student_ids),
                    Fee.is_deleted == False,
                )
                .first()
            )
            total_paid = float(fee_data[0]) if fee_data else 0.0
            total_expected = float(fee_data[1]) if fee_data else 0.0
            fee_rate = round(total_paid / total_expected * 100, 1) if total_expected > 0 else 0.0

            # Placement rate
            placed_count = (
                self.db.query(func.count(Placement.id))
                .filter(Placement.student_id.in_(student_ids))
                .scalar()
                or 0
            )
            placement_rate = (
                round(placed_count / student_count * 100, 1) if student_count > 0 else 0.0
            )

            results.append(
                {
                    "course_id": course.id,
                    "course_name": course.name,
                    "course_code": course.code,
                    "student_count": student_count,
                    "avg_attendance_rate": avg_attendance,
                    "avg_marks_pct": avg_marks,
                    "fee_collection_rate": fee_rate,
                    "placement_rate": placement_rate,
                }
            )

        return results

    def get_attendance_anomalies(self, days: int = 14) -> list[dict[str, Any]]:
        """Detect anomalous attendance patterns.

        Flags students whose attendance rate drops more than 30%
        compared to their personal baseline (overall average), or
        students with sudden streaks of absences.

        Parameters
        ----------
        days : int
            Recent window to check for anomalies (default 14).

        Returns
        -------
        list[dict]
            Each entry: student_id, name, baseline_rate, recent_rate,
            drop_pct, anomaly_type, severity.
        """
        from database.models import Attendance, Student

        now = utc_now()
        recent_cutoff = (now - timedelta(days=days)).date()

        students = self.db.query(Student).all()
        anomalies = []

        for student in students:
            all_records = (
                self.db.query(Attendance).filter(Attendance.student_id == student.id).all()
            )
            if len(all_records) < 5:
                continue

            # Overall baseline (all time)
            total = len(all_records)
            total_present = sum(1 for r in all_records if r.status.value in ("present", "late"))
            baseline_rate = (total_present / total) * 100.0

            # Recent window
            recent_records = [r for r in all_records if r.date >= recent_cutoff]
            if len(recent_records) < 2:
                continue

            recent_present = sum(1 for r in recent_records if r.status.value in ("present", "late"))
            recent_rate = (recent_present / len(recent_records)) * 100.0

            # Check for drop
            drop = baseline_rate - recent_rate
            if drop > 30.0 and baseline_rate > 50.0:
                severity = "high" if drop > 50.0 else "medium"
                anomalies.append(
                    {
                        "student_id": student.id,
                        "name": f"{student.first_name} {student.last_name}",
                        "enrollment_no": student.enrollment_no,
                        "baseline_rate": round(baseline_rate, 1),
                        "recent_rate": round(recent_rate, 1),
                        "drop_pct": round(drop, 1),
                        "recent_records": len(recent_records),
                        "anomaly_type": "attendance_drop",
                        "severity": severity,
                    }
                )

            # Check for absence streak (3+ consecutive absences in recent)
            streak = 0
            for r in sorted(recent_records, key=lambda x: x.date, reverse=True):
                if r.status.value == "absent":
                    streak += 1
                else:
                    break
            if streak >= 3:
                anomalies.append(
                    {
                        "student_id": student.id,
                        "name": f"{student.first_name} {student.last_name}",
                        "enrollment_no": student.enrollment_no,
                        "consecutive_absences": streak,
                        "anomaly_type": "absence_streak",
                        "severity": "high" if streak >= 5 else "medium",
                    }
                )

        # Sort by severity then drop magnitude
        anomalies.sort(
            key=lambda a: (
                0 if a.get("severity") == "high" else 1,
                -a.get("drop_pct", a.get("consecutive_absences", 0)),
            )
        )
        return anomalies[:20]

    def _compute_fee_forecast(self) -> dict[str, Any]:
        """Forecast fee collection for the next 30 days.

        Uses historical collection rates and pending amounts to estimate
        expected collections. Also flags courses with high outstanding
        balances.

        Returns
        -------
        dict with forecast_amount, collection_velocity, at_risk_courses.
        """
        from database.models import Fee, Student

        # Total outstanding balance
        outstanding = (
            self.db.query(func.coalesce(func.sum(Fee.total_amount - Fee.paid_amount), 0))
            .filter(
                Fee.is_deleted == False,
                Fee.status.in_(["unpaid", "partial"]),
            )
            .scalar()
            or 0.0
        )

        # Historical daily collection rate (last 30 days)
        from database.models import FeePayment

        cutoff = date.today() - timedelta(days=30)
        recent_collections = (
            self.db.query(func.coalesce(func.sum(FeePayment.amount), 0))
            .filter(FeePayment.payment_date >= cutoff)
            .scalar()
            or 0.0
        )
        daily_rate = recent_collections / 30.0

        # Project 30-day forecast
        forecast_30d = daily_rate * 30.0

        # Courses with highest outstanding (at-risk)
        from sqlalchemy import text

        course_outstanding = (
            self.db.query(
                Student.course_id,
                func.coalesce(func.sum(Fee.total_amount - Fee.paid_amount), 0).label("outstanding"),
            )
            .join(Fee, Fee.student_id == Student.id)
            .filter(
                Fee.is_deleted == False,
                Fee.status.in_(["unpaid", "partial"]),
            )
            .group_by(Student.course_id)
            .order_by(text("outstanding DESC"))
            .limit(5)
            .all()
        )

        from database.models import Course

        at_risk_courses = []
        for row in course_outstanding:
            course = self.db.query(Course).filter(Course.id == row.course_id).first()
            at_risk_courses.append(
                {
                    "course_id": row.course_id,
                    "course_name": course.name if course else f"Course #{row.course_id}",
                    "outstanding_amount": round(float(row.outstanding), 2),
                }
            )

        return {
            "total_outstanding": round(float(outstanding), 2),
            "daily_collection_rate": round(daily_rate, 2),
            "forecast_30_days": round(forecast_30d, 2),
            "collection_velocity": (
                "strong" if daily_rate > 10000 else "moderate" if daily_rate > 5000 else "slow"
            ),
            "at_risk_courses": at_risk_courses,
        }

    def get_retention_risk_signals(self) -> list[dict[str, Any]]:
        """Identify retention risk signals across the institute.

        Flags students or cohorts showing multiple warning signs:
        - Low attendance (< 60%) + low marks (< 40%) = dual risk
        - Rapid attendance decline (slope < -0.02)
        - High absenteeism + unpaid fees

        Returns
        -------
        list[dict]
            Signal descriptions with severity and student counts.
        """
        from database.models import Attendance, Fee, Result, Student

        now = utc_now()
        cutoff_4wk = (now - timedelta(days=28)).date()
        signals = []

        # 1. Dual risk: low attendance AND low marks
        dual_risk_count = 0
        students = self.db.query(Student).all()
        for student in students:
            recent_att = (
                self.db.query(Attendance)
                .filter(Attendance.student_id == student.id, Attendance.date >= cutoff_4wk)
                .all()
            )
            if len(recent_att) < 2:
                continue
            att_rate = (
                sum(1 for r in recent_att if r.status.value in ("present", "late"))
                / len(recent_att)
            ) * 100.0

            if att_rate < 60.0:
                avg_marks = (
                    self.db.query(func.avg(Result.marks_obtained / Result.total_marks * 100))
                    .filter(
                        Result.student_id == student.id,
                        Result.is_deleted == False,
                        Result.total_marks > 0,
                    )
                    .scalar()
                ) or 0.0
                if avg_marks < 40.0:
                    dual_risk_count += 1

        if dual_risk_count > 0:
            signals.append(
                {
                    "signal": "dual_academic_risk",
                    "label": "Students with low attendance AND low marks",
                    "description": "Students below 60% attendance and 40% average marks need intervention.",
                    "student_count": dual_risk_count,
                    "severity": "high" if dual_risk_count > 20 else "medium",
                }
            )

        # 2. Attendance decline
        decline_count = 0
        for student in students:
            records = (
                self.db.query(Attendance)
                .filter(Attendance.student_id == student.id)
                .order_by(Attendance.date)
                .all()
            )
            if len(records) < 10:
                continue
            window = min(10, len(records))
            recent = records[-window:]
            x_vals = list(range(window))
            y_vals = [1 if r.status.value in ("present", "late") else 0 for r in recent]
            if len(set(y_vals)) < 2:
                continue
            x_mean = sum(x_vals) / window
            y_mean = sum(y_vals) / window
            num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
            den = sum((x - x_mean) ** 2 for x in x_vals)
            slope = num / den if den != 0 else 0.0
            if slope < -0.02:
                decline_count += 1

        if decline_count > 0:
            signals.append(
                {
                    "signal": "attendance_decline",
                    "label": "Students with declining attendance trend",
                    "description": "Attendance slope below -0.02 over last 10 records.",
                    "student_count": decline_count,
                    "severity": "medium",
                }
            )

        # 3. Fee default risk
        default_count = (
            self.db.query(func.count(Fee.id))
            .filter(
                Fee.is_deleted == False,
                Fee.status == "unpaid",
                Fee.due_date < date.today(),
            )
            .scalar()
            or 0
        )
        if default_count > 0:
            signals.append(
                {
                    "signal": "fee_default",
                    "label": "Overdue fee accounts",
                    "description": f"{default_count} overdue fee records requiring attention.",
                    "student_count": default_count,
                    "severity": "high" if default_count > 50 else "medium",
                }
            )

        return signals

    def get_comparative_analytics(self) -> dict[str, Any]:
        """Compare performance across courses and sessions.

        Returns best/worst performing courses by attendance, marks,
        and fee collection for benchmarking.

        Returns
        -------
        dict with top_courses, needs_attention, benchmarks.
        """
        breakdown = self.get_course_performance_breakdown()
        if not breakdown:
            return {"top_courses": [], "needs_attention": [], "benchmarks": {}}

        # Sort by different metrics
        by_attendance = sorted(breakdown, key=lambda c: c["avg_attendance_rate"], reverse=True)
        by_marks = sorted(breakdown, key=lambda c: c["avg_marks_pct"], reverse=True)
        by_fee = sorted(breakdown, key=lambda c: c["fee_collection_rate"], reverse=True)

        # Top/bottom performers
        top_courses = {}
        if by_attendance:
            top_courses["best_attendance"] = by_attendance[0]["course_name"]
            top_courses["worst_attendance"] = (
                by_attendance[-1]["course_name"]
                if len(by_attendance) > 1
                else by_attendance[0]["course_name"]
            )
        if by_marks:
            top_courses["best_marks"] = by_marks[0]["course_name"]
            top_courses["worst_marks"] = (
                by_marks[-1]["course_name"] if len(by_marks) > 1 else by_marks[0]["course_name"]
            )
        if by_fee:
            top_courses["best_fee_collection"] = by_fee[0]["course_name"]

        # Courses needing attention (bottom 3 by avg attendance)
        needs_attention = (
            [
                {
                    "course_name": c["course_name"],
                    "avg_attendance_rate": c["avg_attendance_rate"],
                    "avg_marks_pct": c["avg_marks_pct"],
                }
                for c in by_attendance[-3:]
                if c["avg_attendance_rate"] < 70.0
            ]
            if len(by_attendance) >= 3
            else []
        )

        return {
            "top_courses": top_courses,
            "needs_attention": needs_attention,
            "benchmarks": {
                "overall_avg_attendance": round(
                    sum(c["avg_attendance_rate"] for c in breakdown) / len(breakdown), 1
                ),
                "overall_avg_marks": round(
                    sum(c["avg_marks_pct"] for c in breakdown) / len(breakdown), 1
                ),
                "overall_fee_collection": round(
                    sum(c["fee_collection_rate"] for c in breakdown) / len(breakdown), 1
                ),
            },
        }
