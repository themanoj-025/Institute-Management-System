"""
Unified ML service — the main interface for ML predictions in the app.

Provides:
- ``get_at_risk_students()`` — batch risk assessment for the admin dashboard
- ``predict_student_risk(student_id)`` — single-student prediction with explanation
- ``predict_attendance_trend(student_id)`` — attendance forecast
- ``get_dashboard_kpis()`` — dynamic KPIs computed from the database
- ``train()`` — trigger model training (called on first use or on-demand)

Risk thresholds are read from SystemConfig (admin-configurable) and cached
per session to avoid repeated DB lookups.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import case as sql_case
from sqlalchemy import func

from database.models import Attendance, Fee, Student
from ml.explain import explain_prediction
from ml.features import FEATURE_NAMES, compute_all_features, compute_student_features
from ml.train import load_risk_model, train_risk_model
from utils.time import utc_now

logger = logging.getLogger("ml.service")

# Default thresholds (when SystemConfig is unavailable)

_DEFAULT_ATTENDANCE_RISK = 60.0
_DEFAULT_MARKS_RISK = 40.0
_DEFAULT_HIGH_RISK = 0.7
_DEFAULT_MEDIUM_RISK = 0.5
_DEFAULT_ATT_WINDOW_DAYS = 28


class MLService:
    """High-level ML orchestration service.

    All methods accept an optional ``session`` parameter. If not provided,
    the service creates its own session (for callers that already hold one).

    Usage::

        svc = MLService()
        at_risk = svc.get_at_risk_students(session)
        explanation = svc.predict_student_risk(session, student_id=42)
        kpis = svc.get_dashboard_kpis(session)
    """

    def __init__(self):
        self._model: Any = None
        self._model_name: Optional[str] = None

    def _ensure_model(self, session) -> bool:
        """Load the risk model, training it if none exists.

        Returns ``True`` if a model is available.
        """
        if self._model is not None:
            return True

        model, model_name = load_risk_model()
        if model is None:
            logger.info("No trained model found. Training now...")
            trained, metrics = train_risk_model(session)
            if not trained:
                logger.warning("Model training failed or insufficient data.")
                return False
            model, model_name = load_risk_model()

        self._model = model
        self._model_name = model_name
        return model is not None

    # ── Public API ─────────────────────────────────────────────────

    def train(self, session, force: bool = False) -> Tuple[bool, Dict]:
        """Explicitly trigger model training.

        Parameters
        ----------
        session : Session
        force : bool
            If ``True``, retrain even if a model exists.

        Returns
        -------
        (success, metrics_or_error)
        """
        trained, metrics = train_risk_model(session, force_retrain=force)
        if trained:
            # Reset cached model so next call reloads
            self._model = None
            self._model_name = None
        return trained, metrics

    def get_at_risk_students(
        self, session, threshold: float = 0.5, top_n: int = 20
    ) -> List[Dict[str, Any]]:
        """Return the top-N most at-risk students.

        Uses batch feature computation to avoid N+1 query explosion.
        All students' features are computed in a single DataFrame pass,
        then predictions are made on the entire batch.

        Each entry includes risk score, student info, and top-3 contributing
        factors with explanations.

        Parameters
        ----------
        session : Session
        threshold : float
            Minimum risk probability to include (default 0.5 = 50%).
        top_n : int
            Maximum number of students to return (default 20).

        Returns
        -------
        list[dict]
        """
        if not self._ensure_model(session):
            return self._get_heuristic_at_risk(session, top_n)

        from utils.config import get_config_float

        # Read risk classification thresholds from SystemConfig
        high_risk_threshold = get_config_float(session, "high_risk_threshold", _DEFAULT_HIGH_RISK)
        medium_risk_threshold = get_config_float(
            session, "medium_risk_threshold", _DEFAULT_MEDIUM_RISK
        )

        # Batch-compute features for ALL students in one pass
        X = compute_all_features(session)
        if X.empty:
            return []

        X = X.reindex(columns=FEATURE_NAMES, fill_value=0.0)

        # Batch predict
        probas = self._model.predict_proba(X)[:, 1]

        # Filter by threshold and build results
        students_map = {s.id: s for s in session.query(Student).all()}
        results = []

        for idx, sid in enumerate(X.index):
            if idx >= len(probas):
                break
            proba = float(probas[idx])
            if proba < threshold:
                continue

            student = students_map.get(sid)
            if not student:
                continue

            features = X.loc[sid]
            explanation = explain_prediction(self._model, features, model_version=self._model_name)

            results.append(
                {
                    "student_id": sid,
                    "name": f"{student.first_name} {student.last_name}",
                    "enrollment_no": student.enrollment_no,
                    "course": student.course.name if student.course else "\u2014",
                    "risk_score": round(proba, 4),
                    "risk_level": (
                        "High"
                        if proba >= high_risk_threshold
                        else "Medium" if proba >= medium_risk_threshold else "Low"
                    ),
                    "explanations": explanation,
                }
            )

        results.sort(key=lambda r: r["risk_score"], reverse=True)
        return results[:top_n]

    def predict_student_risk(self, session, student_id: int) -> Optional[Dict[str, Any]]:
        """Predict risk for a single student with full explanation.

        Parameters
        ----------
        session : Session
        student_id : int

        Returns
        -------
        dict or None
            Contains risk_score, risk_level, explanations, and a fallback
            heuristic assessment if the ML model is unavailable.
        """
        if not self._ensure_model(session):
            return self._heuristic_single_risk(session, student_id)

        from utils.config import get_config_float

        # Read risk classification thresholds from SystemConfig
        high_risk_threshold = get_config_float(session, "high_risk_threshold", _DEFAULT_HIGH_RISK)
        medium_risk_threshold = get_config_float(
            session, "medium_risk_threshold", _DEFAULT_MEDIUM_RISK
        )

        try:
            features = compute_student_features(session, student_id)
            if features is None:
                return None

            X = pd.DataFrame(
                [features.reindex(FEATURE_NAMES).fillna(0.0).values],
                columns=FEATURE_NAMES,
            )
            proba = float(self._model.predict_proba(X)[0, 1])

            explanation = explain_prediction(
                self._model,
                features.iloc[0] if hasattr(features, "iloc") else features,
                model_version=self._model_name,
            )
            student = session.query(Student).filter(Student.id == student_id).first()

            return {
                "student_id": student_id,
                "name": f"{student.first_name} {student.last_name}" if student else "\u2014",
                "risk_score": round(proba, 4),
                "risk_level": (
                    "High"
                    if proba >= high_risk_threshold
                    else "Medium" if proba >= medium_risk_threshold else "Low"
                ),
                "model": self._model_name or "unknown",
                "model_version": self._model_name or "",
                "explanations": explanation,
            }
        except Exception as e:
            logger.error("Risk prediction failed for student %d: %s", student_id, e)
            return self._heuristic_single_risk(session, student_id)

    def predict_attendance_trend(self, session, student_id: int) -> Dict[str, Any]:
        """Predict the attendance trend for a student over the next 4 weeks.

        Uses linear regression on recent attendance records.
        This is a simpler statistical model that doesn't require the XGBoost
        classifier.

        Returns
        -------
        dict with trend, prediction, and data points.
        """
        now = utc_now()
        records = (
            session.query(Attendance)
            .filter(Attendance.student_id == student_id)
            .order_by(Attendance.date)
            .all()
        )

        if not records or len(records) < 3:
            return {
                "trend": "Insufficient Data",
                "prediction": 0,
                "next_4wk_forecast": None,
            }

        # Build arrays for linear regression
        n = len(records)
        x = np.arange(n, dtype=float)
        y = np.array(
            [1 if a.status.value in ("present", "late") else 0 for a in records],
            dtype=float,
        )

        # Linear regression via least squares (replacing numpy.polyfit)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        slope = float(numerator / denominator) if denominator != 0 else 0.0
        intercept = float(y_mean - slope * x_mean)

        # Next day prediction
        next_day_pred = slope * n + intercept

        # 4-week forecast: predict attendance for the next 20 class days
        forecast_days = 20
        future_indices = np.arange(n, n + forecast_days, dtype=float)
        future_probs = slope * future_indices + intercept
        future_probs = np.clip(future_probs, 0, 1)
        forecast_rate = float(np.mean(future_probs)) * 100.0

        current_4wk = (
            sum(
                1
                for r in records
                if r.date >= (now - timedelta(days=28)).date()
                and r.status.value in ("present", "late")
            )
            / max(
                len([r for r in records if r.date >= (now - timedelta(days=28)).date()]),
                1,
            )
            * 100.0
        )

        return {
            "trend": "Upward" if slope > 0.01 else "Downward" if slope < -0.01 else "Stable",
            "prediction": round(next_day_pred, 4),
            "current_4wk_rate": round(current_4wk, 1),
            "forecast_4wk_rate": round(forecast_rate, 1),
            "slope": round(slope, 4),
        }

    def get_dashboard_kpis(self, session) -> Dict[str, Any]:
        """Compute dynamic dashboard KPIs from the database.

        Replaces the previous approach of loading entire tables into
        Python memory by using SQL aggregate functions.
        """
        total_students = session.query(Student).count()

        # Fee aggregates via SQL (exclude soft-deleted)
        fee_agg = (
            session.query(
                func.coalesce(func.sum(Fee.total_amount), 0),
                func.coalesce(func.sum(Fee.paid_amount), 0),
            )
            .filter(Fee.is_deleted == False)
            .first()
        )
        total_fees = float(fee_agg[0]) if fee_agg else 0.0
        total_collected = float(fee_agg[1]) if fee_agg else 0.0

        # At-risk count (ML-based, fallback to heuristic)
        at_risk_count = 0
        try:
            at_risk = self.get_at_risk_students(session, threshold=0.5, top_n=1000)
            at_risk_count = len(at_risk)
        except Exception as ml_err:
            logger.warning("ML risk assessment failed, falling back to heuristic: %s", ml_err)
            try:
                from utils.config import get_config_float

                att_threshold = get_config_float(
                    session, "attendance_risk_threshold", _DEFAULT_ATTENDANCE_RISK
                )
                at_risk_count = (
                    session.query(Student)
                    .filter(
                        Student.id.in_(
                            session.query(Attendance.student_id)
                            .group_by(Attendance.student_id)
                            .having(
                                func.avg(
                                    sql_case(
                                        (Attendance.status.in_(["present", "late"]), 1),
                                        else_=0,
                                    )
                                )
                                < (att_threshold / 100.0)
                            )
                        )
                    )
                    .count()
                )
            except Exception as heur_err:
                logger.error("Heuristic fallback also failed: %s", heur_err)
                at_risk_count = 0

        return {
            "total_students": total_students,
            "total_fees_expected": round(total_fees, 2),
            "total_fees_collected": round(total_collected, 2),
            "collection_rate": (
                round((total_collected / total_fees * 100.0), 1) if total_fees else 0.0
            ),
            "at_risk_count": at_risk_count,
            "model_status": "trained" if self._model is not None else "not_loaded",
            "model_version": self._model_name or "",
        }

    # ── Fallback heuristic methods (when ML model is unavailable) ──

    def _get_heuristic_at_risk(self, session, top_n: int = 20) -> List[Dict[str, Any]]:
        """Fallback: identify at-risk students using attendance thresholds.

        Uses a single batch query with GROUP BY instead of per-student loops.
        Returns only the top-N most at-risk (lowest attendance).

        Thresholds are read from SystemConfig (admin-configurable).
        """
        import sqlalchemy as sa

        from utils.config import get_config_float

        att_threshold = get_config_float(
            session, "attendance_risk_threshold", _DEFAULT_ATTENDANCE_RISK
        )
        now = utc_now()
        cutoff = (now - timedelta(days=28)).date()

        # Single batch query: attendance rate per student in last 4 weeks
        att_query = (
            session.query(
                Attendance.student_id,
                sa.func.count(Attendance.id).label("total"),
                sa.func.sum(
                    sa.case((Attendance.status.in_(["present", "late"]), 1), else_=0)
                ).label("present_count"),
            )
            .filter(Attendance.date >= cutoff)
            .group_by(Attendance.student_id)
            .all()
        )

        if not att_query:
            return []

        # Preload students by ID for O(1) lookup
        student_ids = [row.student_id for row in att_query]
        students_map = {
            s.id: s for s in session.query(Student).filter(Student.id.in_(student_ids)).all()
        }

        results = []
        for row in att_query:
            total = row.total or 0
            present = row.present_count or 0
            rate = (present / total * 100.0) if total > 0 else 0.0

            if rate >= att_threshold:
                continue

            student = students_map.get(row.student_id)
            if not student:
                continue

            high_risk_att = att_threshold - 15.0  # e.g., 45% if threshold is 60%
            results.append(
                {
                    "student_id": student.id,
                    "name": f"{student.first_name} {student.last_name}",
                    "enrollment_no": student.enrollment_no,
                    "course": student.course.name if student.course else "\u2014",
                    "risk_score": round(max(0.0, (att_threshold - rate) / att_threshold), 4),
                    "risk_level": "High" if rate < high_risk_att else "Medium",
                    "explanations": [
                        {
                            "name": "attendance_rate_4wk",
                            "label": "Attendance (last 4 weeks)",
                            "value": round(rate, 1),
                            "importance": round(att_threshold - rate, 2),
                            "direction": "increases",
                        }
                    ],
                }
            )

        results.sort(key=lambda r: r["risk_score"], reverse=True)
        return results[:top_n]

    def _heuristic_single_risk(self, session, student_id: int) -> Optional[Dict[str, Any]]:
        """Fallback: heuristic risk assessment for a single student."""
        from utils.config import get_config_float

        att_threshold = get_config_float(
            session, "attendance_risk_threshold", _DEFAULT_ATTENDANCE_RISK
        )
        now = utc_now()
        cutoff = (now - timedelta(days=28)).date()
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            return None

        recent_att = (
            session.query(Attendance)
            .filter(Attendance.student_id == student_id, Attendance.date >= cutoff)
            .all()
        )
        if not recent_att:
            return {
                "student_id": student_id,
                "name": f"{student.first_name} {student.last_name}",
                "risk_score": 0.0,
                "risk_level": "No Data",
                "explanations": [],
            }

        present = sum(1 for a in recent_att if a.status.value in ("present", "late"))
        rate = (present / len(recent_att)) * 100.0

        high_risk_att = att_threshold - 15.0  # e.g., 45% if threshold is 60%

        return {
            "student_id": student_id,
            "name": f"{student.first_name} {student.last_name}",
            "risk_score": round(max(0.0, (att_threshold - rate) / att_threshold), 4),
            "risk_level": (
                "High" if rate < high_risk_att else "Medium" if rate < att_threshold else "Low"
            ),
            "model": "heuristic",
            "model_version": "",
            "explanations": [
                {
                    "name": "attendance_rate_4wk",
                    "label": "Attendance (last 4 weeks)",
                    "value": round(rate, 1),
                    "importance": round(att_threshold - rate, 2),
                    "direction": "increases" if rate < att_threshold else "decreases",
                }
            ],
        }
