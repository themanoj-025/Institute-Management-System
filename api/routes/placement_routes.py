"""Placement routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, require_role, serialize_placement
from api.schemas import PlacementCreate, PlacementPatch, PlacementResponse, paginated_response
from database.db_session import get_session
from database.models import Placement, Student

router = APIRouter(tags=["Placements"])


@router.get("/placements", summary="List placements")
def get_placements(page: int = 1, per_page: int = 25, user: dict = Depends(get_current_user)) -> dict:
    with get_session() as session:
        from sqlalchemy.orm import joinedload

        query = (
            session.query(Placement)
            .options(joinedload(Placement.student))
            .order_by(Placement.id.desc())
        )

        if user["role"] == "student":
            student = session.query(Student).filter(Student.user_id == user["user_id"]).first()
            if student:
                query = query.filter(Placement.student_id == student.id)
            else:
                query = query.filter(Placement.student_id == -1)

        return paginated_response(query, page, per_page, serialize_placement)


@router.post(
    "/placements",
    response_model=PlacementResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create placement record",
)
def create_placement(req: PlacementCreate) -> dict:
    from services.placement_service import PlacementService

    with get_session() as session:
        svc = PlacementService(session)
        placement = svc.create_placement(
            student_id=req.student_id,
            company_name=req.company_name,
            job_title=req.job_title,
            package_lpa=req.package_lpa,
            offer_date=datetime.strptime(req.offer_date, "%Y-%m-%d").date(),
        )
        return placement


@router.patch(
    "/placements/{placement_id}",
    response_model=PlacementResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Patch placement (partial update)",
)
def patch_placement(placement_id: int, req: PlacementPatch) -> dict:
    with get_session() as session:
        placement = session.query(Placement).filter(Placement.id == placement_id).first()
        if not placement:
            raise HTTPException(status_code=404, detail="Placement not found")

        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "offer_date" and value:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            setattr(placement, field, value)
        session.commit()

        return serialize_placement(placement)


@router.delete(
    "/placements/{placement_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete placement",
)
def delete_placement(placement_id: int) -> dict:
    with get_session() as session:
        placement = session.query(Placement).filter(Placement.id == placement_id).first()
        if not placement:
            raise HTTPException(status_code=404, detail="Placement not found")
        session.delete(placement)
        session.commit()
        return {"status": "success", "message": "Placement deleted."}
