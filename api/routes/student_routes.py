"""Student CRUD and bulk attendance/results routes."""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user, require_role, serialize_student
from api.schemas import (
    AttendanceRecord,
    ResultRecord,
    StudentCreate,
    StudentPatch,
    StudentResponse,
)
from database.db_session import get_session
from database.models import Attendance, Course, Result, Student, User, UserRole
from utils.time import utc_now

from datetime import datetime

router = APIRouter(tags=["Students", "Attendance", "Results"])


@router.get(
    "/students",
    summary="List students",
    description="Retrieve a paginated list of student records. Supports filtering by course_id.",
)
def get_students(
    page: int = 1,
    per_page: int = 25,
    course_id: int | None = None,
    user: dict = Depends(get_current_user),
):
    from api.schemas import paginated_response

    with get_session() as session:
        query = session.query(Student)
        return paginated_response(query, page, per_page, serialize_student, course_id=course_id)


@router.get(
    "/students/{student_id}",
    response_model=StudentResponse,
    dependencies=[Depends(require_role(["admin", "staff"]))],
    summary="Get student by ID",
)
def get_student(student_id: int, user: dict = Depends(get_current_user)) -> dict:
    with get_session() as session:
        s = session.query(Student).filter(Student.id == student_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Student record not found")
        return s


@router.post(
    "/students",
    response_model=StudentResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create student",
)
def create_student(req: StudentCreate) -> dict:
    with get_session() as session:
        existing = session.query(User).filter(User.email == req.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already registered in BB-IMS system")

        import secrets as _secrets

        temp_password = f"Stu-{_secrets.token_hex(8)}"
        hashed = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt(14)).decode("utf-8")
        user = User(
            username=req.email.split("@")[0],
            password_hash=hashed,
            role=UserRole.student,
            email=req.email,
        )
        session.add(user)
        session.flush()

        count = session.query(Student).count()
        enroll = f"BB{10000000 + count}"

        student = Student(
            user_id=user.id,
            enrollment_no=enroll,
            first_name=req.first_name,
            last_name=req.last_name,
            dob=datetime.strptime(req.dob, "%Y-%m-%d").date(),
            gender=req.gender,
            course_id=req.course_id,
            session_id=req.session_id,
            admission_date=utc_now().date(),
        )
        session.add(student)
        return student


@router.put(
    "/students/{student_id}",
    response_model=StudentResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Update student (full replace)",
)
def update_student(student_id: int, req: StudentCreate) -> dict:
    with get_session() as session:
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found")
        student.first_name = req.first_name
        student.last_name = req.last_name
        student.dob = datetime.strptime(req.dob, "%Y-%m-%d").date()
        student.gender = req.gender
        student.course_id = req.course_id
        student.session_id = req.session_id
        return student


@router.patch(
    "/students/{student_id}",
    response_model=StudentResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Patch student (partial update)",
)
def patch_student(student_id: int, req: StudentPatch) -> dict:
    with get_session() as session:
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found")
        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "dob" and value:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            if field == "email" and value:
                user = session.query(User).filter(User.id == student.user_id).first()
                if user:
                    user.email = value
            setattr(student, field, value)
        session.commit()
        return student


@router.delete(
    "/students/{student_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete student",
)
def delete_student(student_id: int) -> dict:
    with get_session() as session:
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found")
        session.delete(student)
        session.commit()
        return {"status": "success", "message": "Record successfully removed."}


# --- Bulk Attendance & Results ---


@router.post(
    "/attendance/bulk",
    dependencies=[Depends(require_role(["admin", "staff"]))],
    summary="Record bulk attendance",
    tags=["Attendance"],
)
def bulk_attendance(records: list[AttendanceRecord]) -> dict:
    with get_session() as session:
        for r in records:
            att = Attendance(
                student_id=r.student_id,
                subject_id=r.subject_id,
                session_id=r.session_id,
                date=datetime.strptime(r.date, "%Y-%m-%d").date(),
                status=r.status,
            )
            session.add(att)
        return {"status": "success", "message": f"Successfully entered {len(records)} attendance records."}


@router.post(
    "/results/bulk",
    dependencies=[Depends(require_role(["admin", "staff"]))],
    summary="Register bulk exam results",
    tags=["Results"],
)
def bulk_results(records: list[ResultRecord]) -> dict:
    with get_session() as session:
        for r in records:
            res = Result(
                student_id=r.student_id,
                subject_id=r.subject_id,
                session_id=r.session_id,
                exam_type=r.exam_type,
                marks_obtained=r.marks_obtained,
                total_marks=r.total_marks,
                grade="B",
            )
            session.add(res)
        return {"status": "success", "message": f"Successfully registered {len(records)} results."}
