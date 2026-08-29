from typing import Any

from sqlalchemy.orm import Session

from database.models import Leave, LeaveStatus
from utils.time import utc_now


class LeaveService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def apply_leave(self, data: dict[str, Any]) -> dict:
        leave = Leave(
            student_id=data.get("student_id"),
            staff_id=data.get("staff_id"),
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
            attachment_path=data.get("attachment_path"),
        )
        self.db.add(leave)
        self.db.commit()
        return self._format_leave(leave)

    def get_leaves_for_user(self, student_id: int | None = None, staff_id: int | None = None) -> list[dict]:
        query = self.db.query(Leave)
        if student_id:
            query = query.filter(Leave.student_id == student_id)
        elif staff_id:
            query = query.filter(Leave.staff_id == staff_id)

        leaves = query.order_by(Leave.id.desc()).all()
        return [self._format_leave(leave) for leave in leaves]

    def get_all_leaves(self, status: str | None = None) -> list[dict]:
        query = self.db.query(Leave)
        if status:
            query = query.filter(Leave.status == status)
        leaves = query.order_by(Leave.id.desc()).all()
        return [self._format_leave(leave) for leave in leaves]

    def approve_leave(self, leave_id: int, user_id: int) -> dict | None:
        leave = self.db.query(Leave).filter(Leave.id == leave_id).first()
        if leave:
            leave.status = LeaveStatus.approved
            leave.reviewed_by = user_id
            leave.reviewed_on = utc_now()
            self.db.commit()
        return self._format_leave(leave)

    def reject_leave(self, leave_id: int, user_id: int) -> dict | None:
        leave = self.db.query(Leave).filter(Leave.id == leave_id).first()
        if leave:
            leave.status = LeaveStatus.rejected
            leave.reviewed_by = user_id
            leave.reviewed_on = utc_now()
            self.db.commit()
        return self._format_leave(leave)

    def _format_leave(self, leave: Leave) -> dict:
        applicant = "Unknown"
        if leave.student:
            applicant = f"{leave.student.first_name} {leave.student.last_name} (Student)"
        elif leave.staff:
            applicant = f"{leave.staff.first_name} {leave.staff.last_name} (Staff)"

        return {
            "id": leave.id,
            "applicant": applicant,
            "start_date": leave.start_date.isoformat(),
            "end_date": leave.end_date.isoformat(),
            "reason": leave.reason,
            "status": leave.status.value,
            "applied_on": leave.applied_on.isoformat() if leave.applied_on else None,
        }
