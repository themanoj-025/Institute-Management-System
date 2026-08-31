"""Fee routes with soft-delete support."""

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, require_role, serialize_fee
from api.schemas import PaymentCreate, paginated_response
from database.db_session import get_session
from database.models import Fee, FeeStatus, Student
from utils.time import utc_now

router = APIRouter(tags=["Fees"])


@router.get("/fees", summary="List fee records")
def get_fees(
    page: int = 1,
    per_page: int = 25,
    student_id: int | None = None,
    status: str | None = None,
    include_deleted: bool = False,
    user: dict = Depends(get_current_user),
) -> dict:
    with get_session() as session:
        from sqlalchemy.orm import joinedload

        query = session.query(Fee).options(joinedload(Fee.student)).order_by(Fee.id.desc())

        if not include_deleted:
            query = query.filter(Fee.is_deleted == False)

        if user["role"] == "student":
            student = session.query(Student).filter(Student.user_id == user["user_id"]).first()
            if student:
                query = query.filter(Fee.student_id == student.id)
            else:
                query = query.filter(Fee.student_id == -1)
        elif student_id is not None:
            query = query.filter(Fee.student_id == student_id)

        if status:
            try:
                query = query.filter(Fee.status == FeeStatus(status))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid fee status: '{status}'. Valid values: paid, partial, unpaid",
                )
        return paginated_response(query, page, per_page, serialize_fee)


@router.post(
    "/fees/payment",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Record fee payment",
)
def record_payment(req: PaymentCreate) -> dict:
    from services.fee_service import FeeService

    with get_session() as session:
        svc = FeeService(session)
        try:
            receipt_no = svc.record_payment(
                fee_id=req.fee_id,
                amount=req.amount,
                mode=req.mode,
                transaction_id=req.transaction_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        return {"status": "success", "message": "Payment recorded.", "receipt_no": receipt_no}


@router.delete(
    "/fees/{fee_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Soft-delete fee record",
)
def delete_fee(fee_id: int, permanent: bool = False, user: dict = Depends(get_current_user)) -> dict:
    with get_session() as session:
        fee = session.query(Fee).filter(Fee.id == fee_id).first()
        if not fee:
            raise HTTPException(status_code=404, detail="Fee record not found")

        if permanent:
            session.delete(fee)
        else:
            fee.is_deleted = True
            fee.deleted_at = utc_now()
            fee.deleted_by = user["user_id"]

        session.commit()
        action = "permanently deleted" if permanent else "soft-deleted"
        return {"status": "success", "message": f"Fee record {action}."}


@router.post(
    "/fees/{fee_id}/restore",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Restore soft-deleted fee record",
)
def restore_fee(fee_id: int) -> dict:
    with get_session() as session:
        fee = session.query(Fee).filter(Fee.id == fee_id, Fee.is_deleted).first()
        if not fee:
            raise HTTPException(status_code=404, detail="Deleted fee record not found")

        fee.is_deleted = False
        fee.deleted_at = None
        fee.deleted_by = None
        session.commit()
        return {"status": "success", "message": "Fee record restored."}
