"""Admin routes: risk thresholds, system config, ML promotion history."""

from math import ceil
from typing import Any

from fastapi import APIRouter, Depends

from api.deps import require_role
from api.schemas import RiskThresholdResponse, RiskThresholdUpdate
from database.db_session import get_session
from database.models import PromotionHistory, SystemConfig

router = APIRouter(tags=["Admin"])


def _get_system_config_value(session, key: str, default: Any = None) -> Any:
    """Get a typed value from SystemConfig."""
    entry = session.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not entry:
        return default
    value = entry.value
    value_type = entry.value_type
    if value_type == "int":
        return int(value)
    elif value_type == "float":
        return float(value)
    elif value_type == "bool":
        return value.lower() == "true"
    return value


def _set_system_config_value(
    session, key: str, value: Any, description: str = "", user_id: int | None = None
):
    """Set a typed value in SystemConfig."""
    entry = session.query(SystemConfig).filter(SystemConfig.key == key).first()
    if isinstance(value, bool):
        value_type = "bool"
        str_value = str(value).lower()
    elif isinstance(value, int):
        value_type = "int"
        str_value = str(value)
    elif isinstance(value, float):
        value_type = "float"
        str_value = str(value)
    else:
        value_type = "string"
        str_value = str(value)

    if entry:
        entry.value = str_value
        entry.value_type = value_type
        entry.updated_by = user_id
    else:
        entry = SystemConfig(
            key=key,
            value=str_value,
            value_type=value_type,
            description=description,
            updated_by=user_id,
        )
        session.add(entry)
    session.commit()


@router.get(
    "/admin/config/risk-thresholds",
    response_model=RiskThresholdResponse,
    summary="Get risk thresholds",
)
def get_risk_thresholds(user: dict = Depends(require_role(["admin"]))) -> dict:
    with get_session() as session:
        thresholds = {
            "attendance_risk_threshold": _get_system_config_value(session, "attendance_risk_threshold", 60.0),
            "marks_risk_threshold": _get_system_config_value(session, "marks_risk_threshold", 40.0),
            "high_risk_threshold": _get_system_config_value(session, "high_risk_threshold", 0.7),
            "medium_risk_threshold": _get_system_config_value(session, "medium_risk_threshold", 0.5),
            "attendance_warning_days": _get_system_config_value(session, "attendance_warning_days", 28),
            "drift_detected": _get_system_config_value(session, "drift_detected", "False"),
            "drift_severe": _get_system_config_value(session, "drift_severe", "False"),
            "drift_max_psi": _get_system_config_value(session, "drift_max_psi", "0.0"),
            "drift_max_psi_feature": _get_system_config_value(session, "drift_max_psi_feature", ""),
            "drift_features_drifted": _get_system_config_value(session, "drift_features_drifted", "0"),
            "drift_feature_count": _get_system_config_value(session, "drift_feature_count", "0"),
            "drift_last_checked": _get_system_config_value(session, "drift_last_checked", ""),
            "drift_error": _get_system_config_value(session, "drift_error", ""),
        }
        return {"thresholds": thresholds}


@router.put(
    "/admin/config/risk-thresholds",
    response_model=RiskThresholdResponse,
    summary="Update risk thresholds",
)
def update_risk_thresholds(
    req: RiskThresholdUpdate, user: dict = Depends(require_role(["admin"]))
) -> dict:
    with get_session() as session:
        descriptions = {
            "attendance_risk_threshold": "Attendance percentage below which a student is flagged at-risk",
            "marks_risk_threshold": "Average marks percentage below which a student is flagged at-risk",
            "high_risk_threshold": "ML probability threshold for H risk classification",
            "medium_risk_threshold": "ML probability threshold for MEDIUM risk classification",
            "attendance_warning_days": "Number of days to look back for attendance warnings",
        }
        for key, value in req.thresholds.items():
            _set_system_config_value(session, key, value, description=descriptions.get(key, ""), user_id=user["user_id"])

        thresholds = {}
        for key in descriptions:
            thresholds[key] = _get_system_config_value(
                session,
                key,
                60.0 if "attendance" in key else (40.0 if "marks" in key else 0.7 if "high" in key else 0.5 if "medium" in key else 28),
            )
        return {"thresholds": thresholds}


@router.get(
    "/admin/ml/promotion-history",
    summary="Get ML model promotion history",
)
def get_promotion_history(
    page: int = 1,
    per_page: int = 25,
    user: dict = Depends(require_role(["admin"])),
):
    with get_session() as session:
        query = session.query(PromotionHistory).order_by(PromotionHistory.timestamp.desc())
        total = query.count()
        total_pages = max(ceil(total / per_page), 0) if total > 0 else 0
        rows = query.offset((page - 1) * per_page).limit(per_page).all()

        def _serialize(ph: PromotionHistory) -> dict:
            return {
                "id": ph.id,
                "timestamp": ph.timestamp.isoformat() if ph.timestamp else None,
                "candidate_model_version": ph.candidate_model_version,
                "candidate_auroc": ph.candidate_auroc,
                "candidate_f1": ph.candidate_f1,
                "candidate_precision": ph.candidate_precision,
                "candidate_recall": ph.candidate_recall,
                "active_model_version": ph.active_model_version,
                "active_auroc": ph.active_auroc,
                "promoted": ph.promoted,
                "reason": ph.reason,
            }

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None,
            "data": [_serialize(r) for r in rows],
        }
