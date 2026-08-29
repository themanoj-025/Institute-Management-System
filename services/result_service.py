"""Result service with soft-delete filtering.

All queries against Result filter ``is_deleted == False``
by default, so soft-deleted records are excluded from normal operations.
"""

from typing import Any

from sqlalchemy.orm import Session as DbSession

from database.models import Result


class ResultService:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    def get_existing_marks(self, subject_id: int, session_id: int, exam_type: str) -> dict[int, float]:
        records = (
            self.session.query(Result)
            .filter(
                Result.subject_id == subject_id,
                Result.session_id == session_id,
                Result.exam_type == exam_type,
                Result.is_deleted == False,
            )
            .all()
        )
        return {r.student_id: r.marks_obtained for r in records}

    def get_student_results(self, student_id: int) -> list[dict[str, Any]]:
        results = (
            self.session.query(Result)
            .filter(Result.student_id == student_id, Result.is_deleted == False)
            .all()
        )
        return [
            {
                "subject": r.subject.name,
                "exam_type": r.exam_type,
                "marks": r.marks_obtained,
                "total": r.total_marks,
                "grade": r.grade,
                "pct": (
                    round((r.marks_obtained / r.total_marks) * 100, 1) if r.total_marks > 0 else 0
                ),
            }
            for r in results
        ]

    def bulk_upsert(self, records: list[dict[str, Any]], session_id: int) -> bool:
        for rec in records:
            existing = (
                self.session.query(Result)
                .filter(
                    Result.student_id == rec["student_id"],
                    Result.subject_id == rec["subject_id"],
                    Result.session_id == session_id,
                    Result.exam_type == rec["exam_type"],
                    Result.is_deleted == False,
                )
                .first()
            )

            if existing:
                existing.marks_obtained = rec["marks"]
                existing.total_marks = rec["total"]
                existing.grade = rec["grade"]
            else:
                res = Result(
                    student_id=rec["student_id"],
                    subject_id=rec["subject_id"],
                    session_id=session_id,
                    exam_type=rec["exam_type"],
                    marks_obtained=rec["marks"],
                    total_marks=rec["total"],
                    grade=rec["grade"],
                )
                self.session.add(res)
        self.session.commit()
        return True
