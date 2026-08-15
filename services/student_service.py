import secrets

import bcrypt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config.settings import BCRYPT_COST
from database.models import Student, User, UserRole
from utils.time import utc_now


class StudentService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_students(self, limit=25, offset=0, search_query=None):
        query = self.db.query(Student)

        if search_query:
            query = query.filter(
                or_(
                    Student.first_name.ilike(f"%{search_query}%"),
                    Student.last_name.ilike(f"%{search_query}%"),
                    Student.enrollment_no.ilike(f"%{search_query}%"),
                )
            )

        total = query.count()
        students = query.order_by(Student.id.desc()).limit(limit).offset(offset).all()

        return {"total": total, "students": [self._format_student(s) for s in students]}

    def get_student_by_id(self, student_id):
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError("Student not found")
        return self._format_student(student)

    def create_student(self, data):
        # Create user first with a secure random password
        temp_password = f"Stu-{secrets.token_hex(8)}"
        pw_hash = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt(BCRYPT_COST)).decode(
            "utf-8"
        )
        user = User(
            username=data["username"],
            password_hash=pw_hash,
            role=UserRole.student,
            email=data["email"],
        )
        self.db.add(user)
        self.db.flush()

        student = Student(
            user_id=user.id,
            enrollment_no=data["enrollment_no"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            dob=data["dob"],
            gender=data["gender"],
            address=data.get("address"),
            course_id=data["course_id"],
            session_id=data["session_id"],
            admission_date=data.get("admission_date", utc_now().date()),
        )
        self.db.add(student)
        self.db.commit()
        return self._format_student(student)

    def update_student(self, student_id, data):
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError("Student not found")

        for key, value in data.items():
            if hasattr(student, key):
                setattr(student, key, value)

        self.db.commit()
        return self._format_student(student)

    def delete_student(self, student_id):
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError("Student not found")

        user = student.user
        self.db.delete(student)
        self.db.delete(user)
        self.db.commit()
        return {"status": "success"}

    def _format_student(self, student):
        return {
            "id": student.id,
            "user_id": student.user_id,
            "enrollment_no": student.enrollment_no,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "full_name": f"{student.first_name} {student.last_name}",
            "dob": student.dob.isoformat() if student.dob else None,
            "gender": student.gender,
            "course": student.course.name if student.course else None,
            "course_id": student.course_id,
            "session": student.session.name if student.session else None,
            "session_id": student.session_id,
            "admission_date": (
                student.admission_date.isoformat() if student.admission_date else None
            ),
            "email": student.user.email if student.user else None,
            "username": student.user.username if student.user else None,
            "profile_photo": student.profile_photo,
        }
