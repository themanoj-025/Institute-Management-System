from datetime import date
from typing import Any

from sqlalchemy.orm import Session as DbSession

from database.models import Attendance


class AttendanceService:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    def get_by_date_subject(self, date_val: date, subject_id: int) -> dict[int, str]:
        records = (
            self.session.query(Attendance)
            .filter(Attendance.date == date_val, Attendance.subject_id == subject_id)
            .all()
        )
        return {r.student_id: r.status for r in records}

    def bulk_upsert(self, records: list[dict[str, Any]], staff_id: int) -> bool:
        # records is list of dicts: {"student_id": int, "subject_id": int, "date": "YYYY-MM-DD", "status": "present"/"absent"}
        for rec in records:
            rec_date = (
                date.fromisoformat(rec["date"]) if isinstance(rec["date"], str) else rec["date"]
            )
            existing = (
                self.session.query(Attendance)
                .filter(
                    Attendance.student_id == rec["student_id"],
                    Attendance.subject_id == rec["subject_id"],
                    Attendance.date == rec_date,
                )
                .first()
            )
            if existing:
                existing.status = rec["status"]
            else:
                att = Attendance(
                    student_id=rec["student_id"],
                    subject_id=rec["subject_id"],
                    session_id=rec.get("session_id", 1),
                    date=rec_date,
                    status=rec["status"],
                )
                self.session.add(att)
        self.session.commit()
        return True
