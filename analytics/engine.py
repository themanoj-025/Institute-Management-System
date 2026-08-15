"""
Analytics engine — computes derived metrics and statistical summaries
for the admin dashboard and reporting modules.

Supersedes the original stub by providing real SQL-backed analytics
that were previously scattered across ad-hoc loops in the UI layer.
All heavy lifting is done server-side via SQLAlchemy aggregate queries.

This module is consumed by ``services/analytics_service.py`` and is
separate from the ML prediction pipeline (``ml/``), which handles
at-risk student modelling.
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List

from sqlalchemy import case as sql_case
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import Attendance, AttendanceStatus, Fee, FeeStatus, Placement, Result, Student

logger = logging.getLogger("analytics.engine")

# ═══════════════════════════════════════════════════════════════════
#  ATTENDANCE ANALYTICS
# ═══════════════════════════════════════════════════════════════════


def compute_attendance_summary(
    session: Session,
    days: int = 30,
) -> Dict[str, Any]:
    """Aggregate attendance statistics over the last *days*.

    Returns
    -------
    dict
        ``total_sessions``, ``present_rate``, ``absent_rate``,
        ``late_rate``, ``daily_breakdown`` (list of per-day counts).
    """
    cutoff = date.today() - timedelta(days=days)

    total = session.query(func.count(Attendance.id)).filter(Attendance.date >= cutoff).scalar() or 0

    present = (
        session.query(func.count(Attendance.id))
        .filter(
            Attendance.date >= cutoff,
            Attendance.status == AttendanceStatus.present,
        )
        .scalar()
        or 0
    )

    absent = (
        session.query(func.count(Attendance.id))
        .filter(
            Attendance.date >= cutoff,
            Attendance.status == AttendanceStatus.absent,
        )
        .scalar()
        or 0
    )

    late = (
        session.query(func.count(Attendance.id))
        .filter(
            Attendance.date >= cutoff,
            Attendance.status == AttendanceStatus.late,
        )
        .scalar()
        or 0
    )

    # Daily breakdown
    daily = (
        session.query(
            Attendance.date,
            func.count(Attendance.id).label("total"),
            func.sum(
                sql_case(
                    (Attendance.status == AttendanceStatus.present, 1),
                    else_=0,
                )
            ).label("present_count"),
        )
        .filter(Attendance.date >= cutoff)
        .group_by(Attendance.date)
        .order_by(Attendance.date)
        .all()
    )

    return {
        "period_days": days,
        "total_sessions": total,
        "present_rate": round(present / total * 100, 1) if total else 0.0,
        "absent_rate": round(absent / total * 100, 1) if total else 0.0,
        "late_rate": round(late / total * 100, 1) if total else 0.0,
        "daily_breakdown": [
            {
                "date": row.date.isoformat(),
                "total": row.total,
                "present": row.present_count,
            }
            for row in daily
        ],
    }


def compute_student_attendance_rate(
    session: Session,
    student_id: int,
    days: int = 30,
) -> float:
    """Compute attendance rate for a single student over the last *days*.

    Returns a float between 0 and 100.
    """
    cutoff = date.today() - timedelta(days=days)
    total = (
        session.query(func.count(Attendance.id))
        .filter(
            Attendance.student_id == student_id,
            Attendance.date >= cutoff,
        )
        .scalar()
        or 0
    )
    if total == 0:
        return 0.0

    present = (
        session.query(func.count(Attendance.id))
        .filter(
            Attendance.student_id == student_id,
            Attendance.date >= cutoff,
            Attendance.status.in_([AttendanceStatus.present, AttendanceStatus.late]),
        )
        .scalar()
        or 0
    )
    return round(present / total * 100, 1)


# ═══════════════════════════════════════════════════════════════════
#  FEE ANALYTICS
# ═══════════════════════════════════════════════════════════════════


def compute_fee_summary(session: Session) -> Dict[str, Any]:
    """Aggregate fee collection statistics.

    Respects soft-delete (``is_deleted == False``) on Fee records.
    """
    agg = (
        session.query(
            func.coalesce(func.sum(Fee.total_amount), 0).label("expected"),
            func.coalesce(func.sum(Fee.paid_amount), 0).label("collected"),
            func.count(Fee.id).label("total_records"),
            func.sum(
                sql_case(
                    (Fee.status == FeeStatus.paid, 1),
                    else_=0,
                )
            ).label("paid_count"),
            func.sum(
                sql_case(
                    (Fee.status == FeeStatus.unpaid, 1),
                    else_=0,
                )
            ).label("unpaid_count"),
        )
        .filter(Fee.is_deleted == False)
        .first()
    )

    expected = float(agg.expected) if agg else 0.0
    collected = float(agg.collected) if agg else 0.0
    total_records = int(agg.total_records) if agg else 0
    paid_count = int(agg.paid_count) if agg else 0
    unpaid_count = int(agg.unpaid_count) if agg else 0

    return {
        "total_fees_expected": round(expected, 2),
        "total_fees_collected": round(collected, 2),
        "collection_rate": round(collected / expected * 100, 1) if expected else 0.0,
        "total_records": total_records,
        "paid_count": paid_count,
        "unpaid_count": unpaid_count,
        "outstanding_balance": round(expected - collected, 2),
    }


def compute_overdue_fees(
    session: Session,
    days_threshold: int = 30,
) -> List[Dict[str, Any]]:
    """List fee records overdue by more than *days_threshold*.

    Returns student name, amount, due date, and balance for each.
    """
    cutoff = date.today() - timedelta(days=days_threshold)
    rows = (
        session.query(Fee, Student)
        .join(Student, Fee.student_id == Student.id)
        .filter(
            Fee.is_deleted == False,
            Fee.due_date < cutoff,
            Fee.status != FeeStatus.paid,
        )
        .order_by(Fee.due_date)
        .all()
    )
    return [
        {
            "fee_id": fee.id,
            "student_name": f"{stu.first_name} {stu.last_name}",
            "total_amount": fee.total_amount,
            "paid_amount": fee.paid_amount,
            "balance": fee.total_amount - fee.paid_amount,
            "due_date": fee.due_date.isoformat(),
            "days_overdue": (date.today() - fee.due_date).days,
        }
        for fee, stu in rows
    ]


# ═══════════════════════════════════════════════════════════════════
#  PERFORMANCE / RESULT ANALYTICS
# ═══════════════════════════════════════════════════════════════════


def compute_performance_summary(session: Session) -> Dict[str, Any]:
    """Aggregate result statistics across all students and subjects.

    Respects soft-delete (``is_deleted == False``) on Result records.
    """
    agg = (
        session.query(
            func.avg(Result.marks_obtained / Result.total_marks * 100).label("avg_pct"),
            func.min(Result.marks_obtained / Result.total_marks * 100).label("min_pct"),
            func.max(Result.marks_obtained / Result.total_marks * 100).label("max_pct"),
            func.count(Result.id).label("total_exams"),
        )
        .filter(
            Result.is_deleted == False,
            Result.total_marks > 0,
        )
        .first()
    )

    if not agg or agg.total_exams == 0:
        return {
            "average_percentage": 0.0,
            "min_percentage": 0.0,
            "max_percentage": 0.0,
            "total_exams": 0,
        }

    return {
        "average_percentage": round(float(agg.avg_pct), 1) if agg.avg_pct else 0.0,
        "min_percentage": round(float(agg.min_pct), 1) if agg.min_pct else 0.0,
        "max_percentage": round(float(agg.max_pct), 1) if agg.max_pct else 0.0,
        "total_exams": int(agg.total_exams),
    }


# ═══════════════════════════════════════════════════════════════════
#  PLACEMENT STATISTICS
# ═══════════════════════════════════════════════════════════════════


def compute_placement_summary(session: Session) -> Dict[str, Any]:
    """Aggregate placement statistics."""
    total = session.query(func.count(Placement.id)).scalar() or 0
    avg_package = session.query(func.avg(Placement.package_lpa)).scalar() or 0.0
    max_package = session.query(func.max(Placement.package_lpa)).scalar() or 0.0

    # Top companies by placement count
    top_companies = (
        session.query(
            Placement.company_name,
            func.count(Placement.id).label("count"),
        )
        .group_by(Placement.company_name)
        .order_by(func.count(Placement.id).desc())
        .limit(10)
        .all()
    )

    return {
        "total_placements": total,
        "average_package_lpa": round(float(avg_package), 2),
        "max_package_lpa": round(float(max_package), 2),
        "top_companies": [
            {"name": row.company_name, "placements": row.count} for row in top_companies
        ],
    }


# ═══════════════════════════════════════════════════════════════════
#  TREND / TIMESERIES
# ═══════════════════════════════════════════════════════════════════


def compute_monthly_attendance_trend(
    session: Session,
    months: int = 6,
) -> List[Dict[str, Any]]:
    """Compute monthly attendance rates for trend charts."""
    from calendar import monthrange

    today = date.today()
    results = []
    for i in range(months - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m < 1:
            m += 12
            y -= 1
        _, last_day = monthrange(y, m)

        start = date(y, m, 1)
        end = date(y, m, last_day)

        total = (
            session.query(func.count(Attendance.id))
            .filter(Attendance.date >= start, Attendance.date <= end)
            .scalar()
            or 0
        )
        present = (
            session.query(func.count(Attendance.id))
            .filter(
                Attendance.date >= start,
                Attendance.date <= end,
                Attendance.status.in_([AttendanceStatus.present, AttendanceStatus.late]),
            )
            .scalar()
            or 0
        )

        results.append(
            {
                "month": f"{y}-{m:02d}",
                "rate": round(present / total * 100, 1) if total else 0.0,
                "total_sessions": total,
                "present_count": present,
            }
        )
    return results


# ═══════════════════════════════════════════════════════════════════
#  CLASS: AnalyticsEngine
# ═══════════════════════════════════════════════════════════════════


class AnalyticsEngine:
    """High-level analytics engine for the admin dashboard.

    Wraps the individual compute functions for convenience.
    Usage::

        engine = AnalyticsEngine(session)
        summary = engine.full_summary()
    """

    def __init__(self, session: Session):
        self.session = session

    def attendance_summary(self, days: int = 30) -> Dict[str, Any]:
        return compute_attendance_summary(self.session, days=days)

    def fee_summary(self) -> Dict[str, Any]:
        return compute_fee_summary(self.session)

    def overdue_fees(self, days_threshold: int = 30) -> List[Dict[str, Any]]:
        return compute_overdue_fees(self.session, days_threshold=days_threshold)

    def performance_summary(self) -> Dict[str, Any]:
        return compute_performance_summary(self.session)

    def placement_summary(self) -> Dict[str, Any]:
        return compute_placement_summary(self.session)

    def monthly_attendance_trend(self, months: int = 6) -> List[Dict[str, Any]]:
        return compute_monthly_attendance_trend(self.session, months=months)

    def student_attendance_rate(self, student_id: int, days: int = 30) -> float:
        return compute_student_attendance_rate(self.session, student_id, days=days)

    def full_summary(self) -> Dict[str, Any]:
        """Compute all analytics in a single call."""
        return {
            "attendance": self.attendance_summary(),
            "fees": self.fee_summary(),
            "overdue_fees": self.overdue_fees(),
            "performance": self.performance_summary(),
            "placements": self.placement_summary(),
            "attendance_trend": self.monthly_attendance_trend(),
        }
