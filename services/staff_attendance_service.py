from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from database.models import StaffAttendance


class StaffAttendanceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_staff_attendance(self, staff_id: int, month: Optional[int] = None, year: Optional[int] = None) -> list[dict]:
        query = self.db.query(StaffAttendance).filter(StaffAttendance.staff_id == staff_id)
        if month and year:
            from calendar import monthrange

            _, last_day = monthrange(year, month)
            query = query.filter(
                StaffAttendance.date >= datetime(year, month, 1).date(),
                StaffAttendance.date <= datetime(year, month, last_day).date(),
            )
        records = query.order_by(StaffAttendance.date.desc()).all()
        return [self._format_attendance(r) for r in records]

    def mark_attendance(self, staff_id: int, date: date, status: str, in_time: Optional[datetime] = None, out_time: Optional[datetime] = None) -> dict:
        record = (
            self.db.query(StaffAttendance)
            .filter(StaffAttendance.staff_id == staff_id, StaffAttendance.date == date)
            .first()
        )

        if record:
            record.status = status
            record.in_time = in_time
            record.out_time = out_time
        else:
            record = StaffAttendance(
                staff_id=staff_id,
                date=date,
                status=status,
                in_time=in_time,
                out_time=out_time,
            )
            self.db.add(record)
        self.db.commit()
        return self._format_attendance(record)

    def _format_attendance(self, r: StaffAttendance) -> dict:
        return {
            "id": r.id,
            "date": r.date.isoformat(),
            "status": r.status.value,
            "in_time": r.in_time.strftime("%H:%M") if r.in_time else None,
            "out_time": r.out_time.strftime("%H:%M") if r.out_time else None,
        }
