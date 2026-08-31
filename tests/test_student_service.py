from datetime import date

from database.models import Course, Session, Student

pytestmark = pytest.mark.slow
def test_create_student(test_db, student_service) -> None:
    # Ensure a Course and Session exist
    course = Course(code="PY-1", name="Python Basic", duration_months=3, fee=5000)
    session = Session(name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    test_db.add(course)
    test_db.add(session)
    test_db.commit()

    student_data = {
        "username": "s_jones",
        "email": "jones@student.bb.edu.in",
        "enrollment_no": "BB00000001",
        "first_name": "Samuel",
        "last_name": "Jones",
        "dob": date(2002, 5, 20),
        "gender": "Male",
        "course_id": course.id,
        "session_id": session.id,
    }

    student = student_service.create_student(student_data)
    assert student["id"] is not None
    assert student["enrollment_no"] == "BB00000001"
    assert student["full_name"] == "Samuel Jones"


def test_roll_number_format(test_db, student_service) -> None:
    student = test_db.query(Student).filter(Student.enrollment_no == "BB00000001").first()
    assert student.enrollment_no.startswith("BB")


def test_get_all_paginated(test_db, student_service) -> None:
    # We already have one student. Let's add more to test limit/offset.
    result = student_service.get_all_students(limit=1, offset=0)
    assert len(result["students"]) == 1
    assert result["total"] >= 1
