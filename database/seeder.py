import os
import random
import secrets
import sys
import time
from datetime import date, timedelta

from utils.time import utc_now

import bcrypt
import numpy as np
from faker import Faker
from sqlalchemy import insert, text
from sqlalchemy.orm import Session
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.constants import AVAILABLE_COURSES
from database.db_session import Base, SessionLocal, engine
from database.models import (
    Attendance,
    AttendanceStatus,
    Course,
    CourseModule,
    Fee,
    FeeStatus,
    Notice,
    Placement,
    Result,
)
from database.models import Session as AcadSession
from database.models import (
    Staff,
    Student,
    Subject,
    User,
    UserRole,
)

fake = Faker("en_IN")


def hash_password(password: str) -> str:
    from config.settings import BCRYPT_COST

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(BCRYPT_COST)).decode("utf-8")


def _generate_password() -> str:
    """Generate a secure 16-char random password for seed data."""
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(16))
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
            and any(c in "!@#$%^&*" for c in pw)
        ):
            return pw


def seed_database(db: Session):
    # Check if already seeded
    if db.query(User).count() > 0:
        return

    print("Seeding database... This might take 1-2 minutes.")
    start_time = time.time()

    # Wrap in single transaction and disable FK checks
    db.execute(text("PRAGMA foreign_keys = OFF"))
    try:
        # 1. Admin User — password is random per seed run
        admin_pw_raw = _generate_password()
        admin_pw = hash_password(admin_pw_raw)
        admin = User(
            username="admin",
            password_hash=admin_pw,
            role=UserRole.admin,
            email="admin@binarybrain.edu.in",
            is_active=True,
            email_verified=True,
        )
        db.add(admin)
        db.flush()

        # 2. Courses, Modules, Subjects
        courses_dict = {}
        for c_data in AVAILABLE_COURSES:
            course = Course(
                code=c_data["code"],
                name=c_data["name"],
                duration_months=c_data["duration"],
                fee=c_data["fee"],
                description=f"Learn {c_data['name']} from industry experts.",
            )
            db.add(course)
            db.flush()
            courses_dict[c_data["code"]] = course.id

            # Modules & Subjects (4 modules, 4 subjects per course)
            for i in range(1, 5):
                mod = CourseModule(
                    course_id=course.id, name=f"Module {i} - {c_data['code']}", order=i
                )
                sub = Subject(
                    course_id=course.id,
                    code=f"{c_data['code']}-S{i}",
                    name=f"Subject {i} of {c_data['code']}",
                )
                db.add(mod)
                db.add(sub)
            db.flush()

        # 3. Sessions
        sessions = [
            AcadSession(
                name="2022-23",
                start_date=date(2022, 7, 1),
                end_date=date(2023, 6, 30),
                is_active=False,
            ),
            AcadSession(
                name="2023-24",
                start_date=date(2023, 7, 1),
                end_date=date(2024, 6, 30),
                is_active=False,
            ),
            AcadSession(
                name="2024-25",
                start_date=date(2024, 7, 1),
                end_date=date(2025, 6, 30),
                is_active=True,
            ),
        ]
        db.add_all(sessions)
        db.flush()
        session_ids = [s.id for s in sessions]

        # 4. Staff (50 total, first 3 fixed) — password is random per seed run
        staff_pw_raw = _generate_password()
        staff_pw = hash_password(staff_pw_raw)
        fixed_staff = [
            {
                "user": "dr.sharma",
                "fn": "Rajeev",
                "ln": "Sharma",
                "dept": "Programming",
                "desig": "HOD",
            },
            {
                "user": "prof.mehta",
                "fn": "Sunita",
                "ln": "Mehta",
                "dept": "Data Science",
                "desig": "Senior Professor",
            },
            {
                "user": "ms.khan",
                "fn": "Ayesha",
                "ln": "Khan",
                "dept": "Design",
                "desig": "Assistant Professor",
            },
        ]
        staff_ids = []

        for fs in fixed_staff:
            u = User(
                username=fs["user"],
                password_hash=staff_pw,
                role=UserRole.staff,
                email=f"{fs['user']}@bb.edu.in",
                email_verified=True,
            )
            db.add(u)
            db.flush()
            s = Staff(
                user_id=u.id,
                first_name=fs["fn"],
                last_name=fs["ln"],
                department=fs["dept"],
                designation=fs["desig"],
                join_date=date(2020, 1, 15),
                salary=85000,
            )
            db.add(s)
            db.flush()
            staff_ids.append(s.id)

        for i in range(47):
            u = User(
                username=f"staff{i + 4}",
                password_hash=staff_pw,
                role=UserRole.staff,
                email=f"staff{i + 4}@bb.edu.in",
                email_verified=True,
            )
            db.add(u)
            db.flush()
            s = Staff(
                user_id=u.id,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                department=random.choice(["IT", "CS", "Design", "Math"]),
                designation="Lecturer",
                join_date=fake.date_between(start_date="-5y", end_date="today"),
                salary=random.randint(40000, 90000),
            )
            db.add(s)
            db.flush()
            staff_ids.append(s.id)

        # Assign staff to subjects
        all_subjects = db.query(Subject).all()
        for sub in all_subjects:
            sub.staff_id = random.choice(staff_ids)
        db.flush()

        # 5. Students (5000 total, first 5 fixed) — password is random per seed run
        student_pw_raw = _generate_password()
        student_pw = hash_password(student_pw_raw)
        fixed_students = [
            {
                "user": "rahul.verma",
                "fn": "Rahul",
                "ln": "Verma",
                "course": "MERN",
                "sess": sessions[2].id,
            },
            {
                "user": "priya.singh",
                "fn": "Priya",
                "ln": "Singh",
                "course": "DS",
                "sess": sessions[2].id,
            },
            {
                "user": "arjun.patel",
                "fn": "Arjun",
                "ln": "Patel",
                "course": "CYBER",
                "sess": sessions[2].id,
            },
            {
                "user": "sneha.gupta",
                "fn": "Sneha",
                "ln": "Gupta",
                "course": "AIML",
                "sess": sessions[2].id,
            },
            {
                "user": "dev.joshi",
                "fn": "Dev",
                "ln": "Joshi",
                "course": "DSA",
                "sess": sessions[2].id,
            },
        ]

        course_id_list = list(courses_dict.values())

        # Pre-generate standard users/students in batch using execute(insert)
        users_list = []
        for fs in fixed_students:  # type: ignore
            users_list.append(
                {
                    "username": fs["user"],
                    "password_hash": student_pw,
                    "role": UserRole.student,
                    "email": f"{fs['user']}@student.bb.edu.in",
                    "is_active": True,
                    "email_verified": True,
                    "failed_login_attempts": 0,
                    "created_at": utc_now(),
                }
            )

        for i in range(4995):
            users_list.append(
                {
                    "username": f"student{i + 6}",
                    "password_hash": student_pw,
                    "role": UserRole.student,
                    "email": f"student{i + 6}@student.bb.edu.in",
                    "is_active": True,
                    "email_verified": True,
                    "failed_login_attempts": 0,
                    "created_at": utc_now(),
                }
            )

        db.execute(insert(User), users_list)

        saved_student_users = (
            db.query(User).filter(User.role == UserRole.student).order_by(User.id).all()
        )

        students_list = []
        for idx, u in enumerate(saved_student_users):
            if idx < 5:
                fs = fixed_students[idx]  # type: ignore
                students_list.append(
                    {
                        "user_id": u.id,
                        "enrollment_no": f"BB{10000000 + idx}",
                        "first_name": fs["fn"],
                        "last_name": fs["ln"],
                        "dob": date(2000, 1, 1),
                        "gender": random.choice(["Male", "Female"]),
                        "course_id": courses_dict[fs["course"]],
                        "session_id": fs["sess"],
                        "admission_date": date(2024, 7, 10),
                    }
                )
            else:
                students_list.append(
                    {
                        "user_id": u.id,
                        "enrollment_no": f"BB{10000005 + idx}",
                        "first_name": fake.first_name(),
                        "last_name": fake.last_name(),
                        "dob": fake.date_of_birth(minimum_age=18, maximum_age=25),
                        "gender": random.choice(["Male", "Female"]),
                        "course_id": random.choice(course_id_list),
                        "session_id": random.choice(session_ids),
                        "admission_date": fake.date_between(start_date="-2y", end_date="today"),
                    }
                )

        db.execute(insert(Student), students_list)

        # 6. Bulk Attendance & Results (Vectorized Numpy Decisions)
        all_students = db.query(Student).all()
        attendances_to_add = []
        results_to_add = []
        fees_to_add = []

        print("Generating attendance, results and fees...")

        # Vectorized generation of present/absent statuses
        n_students = len(all_students)
        n_days = 30
        rates = np.array(
            [0.85, 0.92, 0.58, 0.78, 0.45]
            + [random.choice([0.75, 0.80, 0.85, 0.90]) for _ in range(n_students - 5)]
        )
        mask = np.random.random((n_students, n_days)) < rates[:, np.newaxis]

        for idx, s in enumerate(all_students):
            # Fees
            fees_to_add.append(
                {
                    "student_id": s.id,
                    "session_id": s.session_id,
                    "total_amount": 100000.0,
                    "paid_amount": random.choice([100000.0, 50000.0, 0.0]),
                    "due_date": date(2024, 12, 31),
                    "status": FeeStatus.partial,
                    "scholarship_amount": 0.0,
                    "fine_amount": 0.0,
                }
            )

            # Results
            results_to_add.append(
                {
                    "student_id": s.id,
                    "subject_id": all_subjects[0].id,
                    "session_id": s.session_id,
                    "exam_type": "midterm",
                    "marks_obtained": random.uniform(30, 100),
                    "total_marks": 100.0,
                    "grade": "B",
                    "date_declared": date.today(),
                }
            )

            # Attendance
            for d in range(n_days):
                att_date = date(2024, 9, 1) + timedelta(days=d)
                status = AttendanceStatus.present if mask[idx, d] else AttendanceStatus.absent
                attendances_to_add.append(
                    {
                        "student_id": s.id,
                        "subject_id": all_subjects[0].id,
                        "session_id": s.session_id,
                        "date": att_date,
                        "status": status,
                        "remarks": "",
                    }
                )

        # Bulk insert using execute(insert) in chunk batches with tqdm progress bar
        print("Bulk inserting fees...")
        db.execute(insert(Fee), fees_to_add)

        print("Bulk inserting results...")
        db.execute(insert(Result), results_to_add)

        # Batch insert attendance (150,000 records) to keep memory footprint light and speed maximum
        att_batch_size = 20000
        att_batches = [
            attendances_to_add[i : i + att_batch_size]
            for i in range(0, len(attendances_to_add), att_batch_size)
        ]
        for batch in tqdm(att_batches, desc="Seeding attendance"):
            db.execute(insert(Attendance), batch)

        # 7. Notices & Placements
        notices_to_add = [
            {
                "title": f"Notice {i}",
                "content": "Please check the portal for updates.",
                "author_id": admin.id,
                "target_role": "all",
                "is_pinned": False,
                "created_at": utc_now(),
            }
            for i in range(10)
        ]
        db.execute(insert(Notice), notices_to_add)

        placements_to_add = []
        student_subset = random.sample(all_students, min(500, len(all_students)))
        for s in student_subset:
            placements_to_add.append(
                {
                    "student_id": s.id,
                    "company_name": fake.company(),
                    "job_title": fake.job(),
                    "package_lpa": round(random.uniform(3.5, 24.0), 2),
                    "offer_date": fake.date_between(start_date="-1y", end_date="today"),
                }
            )
        db.execute(insert(Placement), placements_to_add)

        db.commit()
        elapsed = time.time() - start_time
        print(f"Done in {elapsed:.1f}s")
        print("Seeding complete.")
        print("\n" + "=" * 60)
        print("SEED CREDENTIALS (save these — they are NOT stored anywhere):")
        print(f"  Admin  : admin / {admin_pw_raw}")
        print(f"  Staff  : dr.sharma / {staff_pw_raw}")
        print(f"  Student: rahul.verma / {student_pw_raw}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Seeding FAILED: {e}. Database rolled back.")
        raise
    finally:
        db.execute(text("PRAGMA foreign_keys = ON"))


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_database(session)
    session.close()
