"""Analytics routes: risk explanation, analytics summary, at-risk students."""

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, require_role
from api.schemas import RiskExplanationResponse
from database.db_session import get_session
from database.models import Student
from utils.logger import setup_logger

logger = setup_logger("bb-ims-api")
router = APIRouter(tags=["Analytics"])


@router.get(
    "/analytics/students/{student_id}/risk-explanation",
    response_model=RiskExplanationResponse,
    summary="Get student risk explanation with SHAP",
)
def get_student_risk_explanation(student_id: int, user: dict = Depends(get_current_user)) -> dict[str, object]:
    from ml.service import MLService

    with get_session() as session:
        if user["role"] == "student":
            owner_user_id = session.query(Student.user_id).filter(Student.id == student_id).scalar()
            if owner_user_id is None or owner_user_id != user["user_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to view this student's risk data.",
                )

        try:
            svc = MLService()
            result = svc.predict_student_risk(session, student_id=student_id)
        except (RuntimeError, ValueError, OSError) as exc:
            logger.error("ML risk prediction failed for student %d: %s", student_id, exc)
            result = None

        if result is None:
            student = session.query(Student).filter(Student.id == student_id).first()
            return {
                "student_id": student_id,
                "name": f"{student.first_name} {student.last_name}" if student else "\u2014",
                "risk_score": None,
                "risk_level": "unknown",
                "model": None,
                "model_version": None,
                "explanations": [
                    {
                        "name": "unavailable",
                        "label": "Prediction unavailable",
                        "value": 0,
                        "importance": 0,
                        "direction": "neutral",
                    }
                ],
            }
        return result


@router.get(
    "/analytics/summary",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Get full analytics summary with chart data",
)
def get_analytics_summary(user: dict = Depends(get_current_user)) -> dict:
    from analytics.engine import AnalyticsEngine
    from services.analytics_service import AnalyticsService

    with get_session() as session:
        engine = AnalyticsEngine(session)
        analytics_svc = AnalyticsService(session)
        summary = engine.full_summary()
        summary["course_performance"] = analytics_svc.get_course_performance_breakdown()
        return summary


@router.get(
    "/analytics/at-risk",
    summary="Get at-risk students",
)
def get_at_risk_students(
    threshold: float = 0.5,
    top_n: int = 20,
    user: dict = Depends(get_current_user),
) -> dict[str, object]:
    from ml.service import MLService

    with get_session() as session:
        try:
            svc = MLService()
            results = svc.get_at_risk_students(session, threshold=threshold, top_n=top_n)
        except (RuntimeError, ValueError, OSError) as exc:
            logger.error("ML get_at_risk_students failed: %s", exc)
            return {"students": [], "count": 0, "error": "ML prediction temporarily unavailable"}
        return {"students": results, "count": len(results)}
