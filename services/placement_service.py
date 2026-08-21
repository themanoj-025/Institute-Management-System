from sqlalchemy.orm import Session

from database.models import Placement


from datetime import date


class PlacementService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_placements(self) -> list[dict]:
        placements = self.db.query(Placement).order_by(Placement.id.desc()).all()
        return [self._format_placement(p) for p in placements]

    def create_placement(self, student_id: int, company_name: str, job_title: str, package_lpa: float, offer_date: date) -> dict:
        placement = Placement(
            student_id=student_id,
            company_name=company_name,
            job_title=job_title,
            package_lpa=package_lpa,
            offer_date=offer_date,
        )
        self.db.add(placement)
        self.db.commit()
        return self._format_placement(placement)

    def _format_placement(self, p: Placement) -> dict:
        return {
            "id": p.id,
            "student_name": (
                f"{p.student.first_name} {p.student.last_name}" if p.student else "Unknown"
            ),
            "company_name": p.company_name,
            "job_title": p.job_title,
            "package_lpa": p.package_lpa,
            "offer_date": p.offer_date.isoformat(),
        }
