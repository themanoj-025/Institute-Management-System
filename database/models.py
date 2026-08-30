import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.db_session import Base
from utils.time import utc_now


# --- Enums ---
class UserRole(enum.Enum):
    admin = "admin"
    staff = "staff"
    student = "student"


class LeaveStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class FeeStatus(enum.Enum):
    paid = "paid"
    partial = "partial"
    unpaid = "unpaid"


class AttendanceStatus(enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"
    excused = "excused"


# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, native_enum=False), nullable=False)
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships — cascade deletes so orphaned profiles are impossible
    staff_profile = relationship(
        "Staff",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    student_profile = relationship(
        "Student",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    activity_logs = relationship(
        "ActivityLog",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notices_authored = relationship(
        "Notice",
        back_populates="author",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    duration_months = Column(Integer, nullable=False)
    fee = Column(Float, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    modules = relationship(
        "CourseModule",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    students = relationship("Student", back_populates="course")
    subjects = relationship(
        "Subject",
        back_populates="course",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CourseModule(Base):
    __tablename__ = "course_modules"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    name = Column(String(100), nullable=False)
    order = Column(Integer, default=1)

    course = relationship("Course", back_populates="modules")


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)

    course = relationship("Course", back_populates="subjects")
    staff = relationship("Staff", back_populates="subjects")
    attendances = relationship(
        "Attendance",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    results = relationship(
        "Result",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    timetables = relationship(
        "Timetable",
        back_populates="subject",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_subjects_course_id", "course_id"),
        Index("ix_subjects_staff_id", "staff_id"),
    )


class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    department = Column(String(50))
    designation = Column(String(50))
    qualification = Column(String(100))
    join_date = Column(Date, nullable=False)
    salary = Column(Float)
    address = Column(Text)
    profile_photo = Column(String(255))
    bank_account = Column(String(50))
    ifsc_code = Column(String(20))

    user = relationship("User", back_populates="staff_profile")
    subjects = relationship("Subject", back_populates="staff")
    leaves = relationship(
        "Leave",
        back_populates="staff",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attendances = relationship(
        "StaffAttendance",
        back_populates="staff",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    timetables = relationship("Timetable", back_populates="staff")


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # e.g., 2023-2024
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)

    students = relationship("Student", back_populates="session")
    attendances = relationship("Attendance", back_populates="session")
    results = relationship("Result", back_populates="session")
    fees = relationship("Fee", back_populates="session")


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    enrollment_no = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    dob = Column(Date, nullable=False)
    gender = Column(String(10))
    address = Column(Text)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    admission_date = Column(Date, nullable=False)
    guardian_name = Column(String(100))
    guardian_phone = Column(String(20))
    profile_photo = Column(String(255))

    user = relationship("User", back_populates="student_profile")
    course = relationship("Course", back_populates="students")
    session = relationship("Session", back_populates="students")
    attendances = relationship(
        "Attendance",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    results = relationship(
        "Result",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    leaves = relationship(
        "Leave",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    fees = relationship(
        "Fee",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    placements = relationship(
        "Placement",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_students_course_id", "course_id"),
        Index("ix_students_session_id", "session_id"),
    )


class Attendance(Base):
    __tablename__ = "attendances"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(AttendanceStatus, native_enum=False), nullable=False)
    remarks = Column(String(255))

    student = relationship("Student", back_populates="attendances")
    subject = relationship("Subject", back_populates="attendances")
    session = relationship("Session", back_populates="attendances")

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "session_id",
            "date",
            name="uq_attendance_student_subject_session_date",
        ),
        Index("ix_attendances_student_id", "student_id"),
        Index("ix_attendances_subject_id", "subject_id"),
        Index("ix_attendances_session_id", "session_id"),
        Index("ix_attendances_date", "date"),
    )


class StaffAttendance(Base):
    __tablename__ = "staff_attendances"
    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(AttendanceStatus, native_enum=False), nullable=False)
    in_time = Column(Time)
    out_time = Column(Time)

    staff = relationship("Staff", back_populates="attendances")

    __table_args__ = (UniqueConstraint("staff_id", "date", name="uq_staff_attendance_staff_date"),)


class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    exam_type = Column(String(50), nullable=False)
    marks_obtained = Column(Float, nullable=False)
    total_marks = Column(Float, nullable=False)
    grade = Column(String(5))
    date_declared = Column(Date, default=utc_now)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    student = relationship("Student", back_populates="results")
    subject = relationship("Subject", back_populates="results")
    session = relationship("Session", back_populates="results")

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "exam_type",
            name="uq_result_student_subject_exam",
        ),
        Index("ix_results_student_id", "student_id"),
        Index("ix_results_subject_id", "subject_id"),
        Index("ix_results_session_id", "session_id"),
        Index("ix_results_is_deleted", "is_deleted"),
    )



# Re-export extended models for backward compatibility
from database.models_extended import (  # noqa: F401, E402
    Leave,
    Feedback,
    Fee,
    FeePayment,
    Notice,
    Timetable,
    ActivityLog,
    Enquiry,
    SystemConfig,
    OtpCode,
    RevokedToken,
    EmailVerificationToken,
    PromotionHistory,
    PasswordResetToken,
    Placement,
)
