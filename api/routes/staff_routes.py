"""Staff CRUD routes."""

from datetime import datetime

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, require_role, serialize_staff
from api.schemas import StaffCreate, StaffPatch, StaffResponse, paginated_response
from database.db_session import get_session
from database.models import Staff, User, UserRole

router = APIRouter(tags=["Staff"])


@router.get("/staff", summary="List staff")
def get_staff(
    page: int = 1,
    per_page: int = 25,
    department: str | None = None,
    user: dict = Depends(get_current_user),
):
    with get_session() as session:
        from sqlalchemy.orm import joinedload

        query = session.query(Staff).options(joinedload(Staff.user))
        return paginated_response(query, page, per_page, serialize_staff, department=department)


@router.get("/staff/{staff_id}", response_model=StaffResponse, summary="Get staff member by ID")
def get_staff_member(staff_id: int, user: dict = Depends(get_current_user)) -> dict:
    with get_session() as session:
        st = session.query(Staff).filter(Staff.id == staff_id).first()
        if not st:
            raise HTTPException(status_code=404, detail="Staff record not found")
        return st


@router.post(
    "/staff",
    response_model=StaffResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create staff member",
)
def create_staff(req: StaffCreate) -> dict:
    with get_session() as session:
        existing = session.query(User).filter(User.email == req.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already registered")

        import secrets as _secrets

        temp_password = f"Stf-{_secrets.token_hex(8)}"
        hashed = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt(14)).decode("utf-8")
        user = User(
            username=req.email.split("@")[0],
            password_hash=hashed,
            role=UserRole.staff,
            email=req.email,
        )
        session.add(user)
        session.flush()

        staff = Staff(
            user_id=user.id,
            first_name=req.first_name,
            last_name=req.last_name,
            department=req.department,
            designation=req.designation,
            join_date=datetime.strptime(req.join_date, "%Y-%m-%d").date(),
            salary=req.salary or 0.0,
        )
        session.add(staff)
        session.commit()
        return staff


@router.put(
    "/staff/{staff_id}",
    response_model=StaffResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Update staff (full replace)",
)
def update_staff(staff_id: int, req: StaffCreate) -> dict:
    with get_session() as session:
        staff = session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff record not found")
        staff.first_name = req.first_name
        staff.last_name = req.last_name
        staff.department = req.department
        staff.designation = req.designation
        staff.join_date = datetime.strptime(req.join_date, "%Y-%m-%d").date()
        staff.salary = req.salary or 0.0
        session.commit()
        return staff


@router.patch(
    "/staff/{staff_id}",
    response_model=StaffResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Patch staff (partial update)",
)
def patch_staff(staff_id: int, req: StaffPatch) -> dict:
    with get_session() as session:
        staff = session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff record not found")
        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "join_date" and value:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            if field == "email" and value:
                user = session.query(User).filter(User.id == staff.user_id).first()
                if user:
                    user.email = value
            setattr(staff, field, value)
        session.commit()
        return staff


@router.delete(
    "/staff/{staff_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete staff member",
)
def delete_staff(staff_id: int) -> dict:
    with get_session() as session:
        staff = session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff record not found")
        session.delete(staff)
        session.commit()
        return {"status": "success", "message": "Staff record deleted."}
