from sqlalchemy.orm import Session

from database.models import Course


class CourseService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_courses(self):
        courses = self.db.query(Course).all()
        return [self._format_course(c) for c in courses]

    def get_course_details(self, course_id):
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError("Course not found")

        data = self._format_course(course)
        data["modules"] = [{"id": m.id, "name": m.name, "order": m.order} for m in course.modules]
        data["subjects"] = [{"id": s.id, "code": s.code, "name": s.name} for s in course.subjects]
        return data

    def _format_course(self, course):
        return {
            "id": course.id,
            "code": course.code,
            "name": course.name,
            "duration": course.duration_months,
            "fee": course.fee,
            "description": course.description,
        }
