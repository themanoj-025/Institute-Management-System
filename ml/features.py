"""
Feature engineering pipeline for ML prediction models.

Computes student-level features from the database tables:
attendance, results, fees, leaves, and student metadata.

All queries filter ``is_deleted == False`` on soft-deletable tables.
Risk thresholds are read from ``SystemConfig``, falling back to sensible defaults.
"""

import logging
from datetime import timedelta
from typing import Dict, List

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from database.models import (
    Attendance,
    AttendanceStatus,
    Fee,
    FeeStatus,
    Leave,
    Result,
    Student,
)
from utils.time import utc_now

# Feature names registry (used by SHAP explainer)

FEATURE_NAMES = [
    "attendance_rate_4wk",
    "attendance_rate_8wk",
    "attendance_rate_overall",
    "attendance_trend_slope",
    "marks_avg",
    "marks_trend_slope",
    "marks_completion_rate",
    "leave_count_this_term",
    "leave_days_total",
    "fee_payment_ratio",
    "fee_overdue_count",
    "gender_male",
    "course_id",
]

# Default thresholds (used when SystemConfig is unavailable)

_DEFAULT_ATTENDANCE_RISK_THRESHOLD = 60.0
_DEFAULT_MARKS_RISK_THRESHOLD = 40.0


def _compute_attendance_features(session: Session, student_id: int, now) -> dict:
    """Compute attendance-based features for a single student."""
    records = (
        session.query(Attendance)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.date)
        .all()
    )

    if not records:
        return {
            "attendance_rate_4wk": 0.0,
            "attendance_rate_8wk": 0.0,
            "attendance_rate_overall": 0.0,
            "attendance_trend_slope": 0.0,
        }

    total = len(records)
    present_count = sum(
        1 for r in records if r.status in (AttendanceStatus.present, AttendanceStatus.late)
    )
    overall_rate = (present_count / total) * 100.0 if total > 0 else 0.0

    # Sliding windows
    four_weeks_ago = now - timedelta(days=28)
    eight_weeks_ago = now - timedelta(days=56)

    recent_4wk = [r for r in records if r.date >= four_weeks_ago.date()]
    recent_8wk = [r for r in records if r.date >= eight_weeks_ago.date()]

    rate_4wk = (
        sum(1 for r in recent_4wk if r.status in (AttendanceStatus.present, AttendanceStatus.late))
        / len(recent_4wk)
        * 100.0
        if recent_4wk
        else overall_rate
    )

    rate_8wk = (
        sum(1 for r in recent_8wk if r.status in (AttendanceStatus.present, AttendanceStatus.late))
        / len(recent_8wk)
        * 100.0
        if recent_8wk
        else overall_rate
    )

    # Trend slope — linear regression over last 10 attendance records (or fewer)
    # Uses simple least-squares formula instead of numpy.polyfit
    window = min(10, len(records))
    recent = records[-window:]
    x = np.arange(window, dtype=float)
    y = np.array(
        [1 if r.status in (AttendanceStatus.present, AttendanceStatus.late) else 0 for r in recent],
        dtype=float,
    )
    if window >= 3 and np.ptp(y) > 0:  # ptp = peak-to-peak (range)
        # Linear regression via least squares: slope = sum((x-x_mean)*(y-y_mean)) / sum((x-x_mean)^2)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        slope = float(numerator / denominator) if denominator != 0 else 0.0
    else:
        slope = 0.0

    return {
        "attendance_rate_4wk": round(rate_4wk, 1),
        "attendance_rate_8wk": round(rate_8wk, 1),
        "attendance_rate_overall": round(overall_rate, 1),
        "attendance_trend_slope": round(slope, 4),
    }


def _compute_marks_features(session: Session, student_id: int) -> dict:
    """Compute marks/result-based features.

    Filters out soft-deleted results (is_deleted == False).
    """
    results = (
        session.query(Result)
        .filter(Result.student_id == student_id, Result.is_deleted == False)
        .order_by(Result.date_declared)
        .all()
    )

    if not results:
        return {
            "marks_avg": 0.0,
            "marks_trend_slope": 0.0,
            "marks_completion_rate": 0.0,
        }

    pcts = [(r.marks_obtained / r.total_marks) * 100.0 for r in results if r.total_marks > 0]
    avg_pct = float(np.mean(pcts)) if pcts else 0.0

    # Trend: slope of last 5 exam scores
    window = min(5, len(pcts))
    recent = np.array(pcts[-window:], dtype=float)
    if window >= 3 and np.ptp(recent) > 0:
        x = np.arange(window, dtype=float)
        x_mean = np.mean(x)
        y_mean = np.mean(recent)
        numerator = np.sum((x - x_mean) * (recent - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        slope = float(numerator / denominator) if denominator != 0 else 0.0
    else:
        slope = 0.0

    # How many subjects have at least one result vs total subjects enrolled
    enrolled_subjects = (
        session.query(Result.subject_id)
        .filter(Result.student_id == student_id, Result.is_deleted == False)
        .distinct()
        .count()
    )
    # Rough completion: assume ~6 subjects per course
    completion = min(1.0, enrolled_subjects / 6.0) if enrolled_subjects > 0 else 0.0

    return {
        "marks_avg": round(avg_pct, 1),
        "marks_trend_slope": round(slope, 4),
        "marks_completion_rate": round(completion * 100.0, 1),
    }


def _compute_leave_features(session: Session, student_id: int) -> dict:
    """Compute leave-based features."""
    leaves = session.query(Leave).filter(Leave.student_id == student_id).all()

    if not leaves:
        return {"leave_count_this_term": 0, "leave_days_total": 0}

    total_days = sum(
        max(0, (lv.end_date - lv.start_date).days + 1)
        for lv in leaves
        if lv.start_date and lv.end_date
    )
    return {
        "leave_count_this_term": len(leaves),
        "leave_days_total": total_days,
    }


def _compute_fee_features(session: Session, student_id: int) -> dict:
    """Compute fee-based features.

    Filters out soft-deleted fees (is_deleted == False).
    """
    fees = session.query(Fee).filter(Fee.student_id == student_id, Fee.is_deleted == False).all()

    if not fees:
        return {"fee_payment_ratio": 0.0, "fee_overdue_count": 0}

    total_amount = sum(f.total_amount for f in fees)
    total_paid = sum(f.paid_amount for f in fees)
    payment_ratio = (total_paid / total_amount * 100.0) if total_amount > 0 else 0.0
    overdue_count = sum(1 for f in fees if f.status != FeeStatus.paid)

    return {
        "fee_payment_ratio": round(payment_ratio, 1),
        "fee_overdue_count": overdue_count,
    }


def compute_student_features(session: Session, student_id: int) -> pd.Series:
    """Compute all ML features for a single student.

    Returns a pandas Series with named features suitable for model input.
    """
    now = utc_now()
    student = session.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise ValueError(f"Student {student_id} not found")

    att = _compute_attendance_features(session, student_id, now)
    marks = _compute_marks_features(session, student_id)
    leaves = _compute_leave_features(session, student_id)
    fee = _compute_fee_features(session, student_id)

    features = {
        **att,
        **marks,
        **leaves,
        **fee,
        "gender_male": 1 if student.gender and student.gender.lower() == "male" else 0,
        "course_id": float(student.course_id),
    }

    return pd.Series(features, name=student_id)


def compute_all_features(session: Session) -> pd.DataFrame:
    """Compute features for all students and return a DataFrame.

    Rows: students, Columns: features.
    Used for batch model training.
    """
    student_ids = [s.id for s in session.query(Student.id).all()]
    rows: List[pd.Series] = []

    for sid in student_ids:
        try:
            rows.append(compute_student_features(session, sid))
        except Exception as e:
            logger.debug("Skipping student %d during batch feature computation: %s", sid, e)
            continue

    if not rows:
        return pd.DataFrame(columns=FEATURE_NAMES)

    df = pd.DataFrame(rows)
    # Fill any NaN values with 0
    df = df.fillna(0.0)
    return df


def compute_target(session: Session) -> pd.Series:
    """Compute the target variable for each student.

    Target: 1 if at-risk (attendance < threshold OR avg marks < threshold), else 0.

    Risk thresholds are read from SystemConfig (admin-configurable), falling back
    to sensible defaults (60% attendance, 40% marks) if not configured.

    Returns a Series indexed by student_id.
    """
    now = utc_now()

    from utils.config import get_config_float

    # Read thresholds from SystemConfig (admin-configurable)
    att_threshold = get_config_float(
        session, "attendance_risk_threshold", _DEFAULT_ATTENDANCE_RISK_THRESHOLD
    )
    marks_threshold = get_config_float(
        session, "marks_risk_threshold", _DEFAULT_MARKS_RISK_THRESHOLD
    )

    student_ids = [s.id for s in session.query(Student.id).all()]
    targets: Dict[int, int] = {}

    for sid in student_ids:
        try:
            att = _compute_attendance_features(session, sid, now)
            marks = _compute_marks_features(session, sid)

            overall_att = att["attendance_rate_overall"]
            avg_marks = marks["marks_avg"]

            # A student is at risk if attendance < threshold OR marks < threshold
            is_at_risk = 1 if (overall_att < att_threshold or avg_marks < marks_threshold) else 0
            targets[sid] = is_at_risk
        except Exception as e:
            logger.debug("Skipping target computation for student %d: %s", sid, e)
            targets[sid] = 0

    return pd.Series(targets, name="at_risk")
