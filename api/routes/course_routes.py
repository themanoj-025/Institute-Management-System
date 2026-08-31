"""Course CRUD routes."""

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, require_role, serialize_course
from api.schemas import CourseCreate, CoursePatch, CourseResponse, paginated_response
from database.db_session import get_session
from database.models import Course

router = APIRouter(tags=["Courses"])


@router.get("/courses", summary="List courses")
def get_courses(page: int = 1, per_page: int = 25, user: dict = Depends(get_current_user)) -> dict:
    with get_session() as session:
        query = session.query(Course).order_by(Course.id)
        return paginated_response(query, page, per_page, serialize_course)


@router.get("/courses/{course_id}", summary="Get course by ID")
def get_course(course_id: int, user: dict = Depends(get_current_user)) -> dict:
    with get_session() as session:
        from sqlalchemy.orm import joinedload

        c = (
            session.query(Course)
            .options(joinedload(Course.modules), joinedload(Course.subjects))
            .filter(Course.id == course_id)
            .first()
        )
        if not c:
            raise HTTPException(status_code=404, detail="Course not found")
        result = serialize_course(c)
        result["modules"] = [{"id": m.id, "name": m.name, "order": m.order} for m in c.modules]
        result["subjects"] = [{"id": s.id, "code": s.code, "name": s.name} for s in c.subjects]
        return result


@router.post(
    "/courses",
    response_model=CourseResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create course",
)
def create_course(req: CourseCreate) -> dict:
    with get_session() as session:
        existing = session.query(Course).filter(Course.code == req.code).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Course code '{req.code}' already exists")
        course = Course(
            code=req.code,
            name=req.name,
            duration_months=req.duration_months,
            fee=req.fee,
            description=req.description,
        )
        session.add(course)
        session.commit()
        return course


@router.put(
    "/courses/{course_id}",
    response_model=CourseResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Update course (full replace)",
)
def update_course(course_id: int, req: CourseCreate) -> dict:
    with get_session() as session:
        course = session.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        course.code = req.code
        course.name = req.name
        course.duration_months = req.duration_months
        course.fee = req.fee
        course.description = req.description
        session.commit()
        return course


@router.patch(
    "/courses/{course_id}",
    response_model=CourseResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Patch course (partial update)",
)
def patch_course(course_id: int, req: CoursePatch) -> dict:
    with get_session() as session:
        course = session.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(course, field, value)
        session.commit()
        return course


@router.delete(
    "/courses/{course_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete course",
)
def delete_course(course_id: int) -> dict:
    with get_session() as session:
        course = session.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        session.delete(course)
        session.commit()
        return {"status": "success", "message": "Course deleted."}
