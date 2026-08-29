import secrets

import bcrypt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config.settings import BCRYPT_COST
from database.models import Staff, User, UserRole


class StaffService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_staff(self, limit: int = 25, offset: int = 0, search_query: str | None = None) -> dict:
        query = self.db.query(Staff)

        if search_query:
            query = query.filter(
                or_(
                    Staff.first_name.ilike(f"%{search_query}%"),
                    Staff.last_name.ilike(f"%{search_query}%"),
                    Staff.department.ilike(f"%{search_query}%"),
                )
            )

        total = query.count()
        staff_list = query.order_by(Staff.id.desc()).limit(limit).offset(offset).all()

        return {"total": total, "staff": [self._format_staff(s) for s in staff_list]}

    def get_staff_by_id(self, staff_id: int) -> dict:
        staff = self.db.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise ValueError("Staff not found")
        return self._format_staff(staff)

    def create_staff(self, data: dict) -> dict:
        # Generate a secure random password for the new staff member
        temp_password = f"Stf-{secrets.token_hex(8)}"
        pw_hash = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt(BCRYPT_COST)).decode(
            "utf-8"
        )
        user = User(
            username=data["username"],
            password_hash=pw_hash,
            role=UserRole.staff,
            email=data["email"],
        )
        self.db.add(user)
        self.db.flush()

        staff = Staff(
            user_id=user.id,
            first_name=data["first_name"],
            last_name=data["last_name"],
            department=data.get("department"),
            designation=data.get("designation"),
            join_date=data["join_date"],
            salary=data.get("salary", 0.0),
        )
        self.db.add(staff)
        self.db.commit()
        return self._format_staff(staff)

    def _format_staff(self, staff: Staff) -> dict:
        return {
            "id": staff.id,
            "user_id": staff.user_id,
            "first_name": staff.first_name,
            "last_name": staff.last_name,
            "full_name": f"{staff.first_name} {staff.last_name}",
            "department": staff.department,
            "designation": staff.designation,
            "join_date": staff.join_date.isoformat() if staff.join_date else None,
            "email": staff.user.email if staff.user else None,
            "username": staff.user.username if staff.user else None,
            "profile_photo": staff.profile_photo,
        }
