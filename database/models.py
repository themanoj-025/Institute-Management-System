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
    role = Column(Enum(UserRole), nullable=False)  # type: ignore[call-overload]
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
    status = Column(Enum(AttendanceStatus), nullable=False)  # type: ignore[call-overload]
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
    status = Column(Enum(AttendanceStatus), nullable=False)  # type: ignore[call-overload]
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


class Leave(Base):
    __tablename__ = "leaves"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.pending)  # type: ignore[call-overload]
    applied_on = Column(DateTime(timezone=True), default=utc_now)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_on = Column(DateTime(timezone=True), nullable=True)
    attachment_path = Column(String(255))

    student = relationship("Student", back_populates="leaves")
    staff = relationship("Staff", back_populates="leaves")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_leaves_student_id", "student_id"),
        Index("ix_leaves_staff_id", "staff_id"),
        Index("ix_leaves_status", "status"),
    )


class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    submitted_on = Column(DateTime(timezone=True), default=utc_now)
    reply = Column(Text)
    replied_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    replied_on = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    replier = relationship("User", foreign_keys=[replied_by])


class Fee(Base):
    __tablename__ = "fees"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(FeeStatus), default=FeeStatus.unpaid)  # type: ignore[call-overload]
    scholarship_amount = Column(Float, default=0.0)
    fine_amount = Column(Float, default=0.0)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    student = relationship("Student", back_populates="fees")
    session = relationship("Session", back_populates="fees")
    payments = relationship(
        "FeePayment",
        back_populates="fee",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    deleter = relationship("User", foreign_keys=[deleted_by])

    __table_args__ = (
        Index("ix_fees_student_id", "student_id"),
        Index("ix_fees_session_id", "session_id"),
        Index("ix_fees_is_deleted", "is_deleted"),
    )


class FeePayment(Base):
    __tablename__ = "fee_payments"
    id = Column(Integer, primary_key=True, index=True)
    fee_id = Column(Integer, ForeignKey("fees.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime(timezone=True), default=utc_now)
    payment_mode = Column(String(50))  # Cash, UPI, Bank Transfer
    transaction_id = Column(String(100))
    receipt_no = Column(String(50), unique=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    fee = relationship("Fee", back_populates="payments")

    __table_args__ = (Index("ix_fee_payments_fee_id", "fee_id"),)


class Notice(Base):
    __tablename__ = "notices"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_role = Column(String(50), default="all")  # all, staff, student
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    author = relationship("User", back_populates="notices_authored")

    __table_args__ = (Index("ix_notices_author_id", "author_id"),)


class Timetable(Base):
    __tablename__ = "timetables"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    day_of_week = Column(String(15), nullable=False)  # Monday, Tuesday...
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room_no = Column(String(50))

    course = relationship("Course")
    subject = relationship("Subject", back_populates="timetables")
    staff = relationship("Staff", back_populates="timetables")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)
    module = Column(String(100))
    ip_address = Column(String(50))
    timestamp = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="activity_logs")

    __table_args__ = (
        Index("ix_activity_logs_user_id", "user_id"),
        Index("ix_activity_logs_timestamp", "timestamp"),
    )


class Enquiry(Base):
    __tablename__ = "enquiries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20))
    message = Column(Text, nullable=False)
    course_interest = Column(String(100))
    submitted_at = Column(DateTime(timezone=True), default=utc_now)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"))
    resolved_at = Column(DateTime(timezone=True))


class SystemConfig(Base):
    """Key-value configuration store for admin-configurable system settings.

    Stores risk thresholds, feature flags, and other tunables.
    Values are cached in memory and invalidated on update.
    """

    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), default="string")  # string, int, float, bool
    description = Column(Text)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class OtpCode(Base):
    """Server-side OTP store with hashed codes and TTL.

    Replaces the in-memory dict from auth_service with a persistent,
    auditable table. OTP codes are hashed (SHA-256) before storage
    and never returned in any API response.
    """

    __tablename__ = "otp_codes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)  # SHA-256 hex digest
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (Index("ix_otp_codes_user_id_expires", "user_id", "expires_at"),)


class RevokedToken(Base):
    """Server-side JWT token blacklist.

    Stores the JTI of revoked tokens with their original expiry so
    the blacklist entry can be auto-cleaned by TTL or a background job.
    """

    __tablename__ = "revoked_tokens"
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(64), unique=True, nullable=False, index=True)
    token_type = Column(String(20), default="access")  # access, refresh
    revoked_at = Column(DateTime(timezone=True), default=utc_now)
    expires_at = Column(
        DateTime(timezone=True), nullable=False
    )  # When the token would have expired
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (Index("ix_revoked_tokens_expires", "expires_at"),)


class EmailVerificationToken(Base):
    """Server-side email verification token store.

    Generated when a new account is created or when a user requests
    a new verification email. Tokens are hashed (SHA-256) before
    storage, single-use, and expire after 24 hours.
    """

    __tablename__ = "email_verification_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False)  # SHA-256 hex digest
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_email_verification_user_id", "user_id"),
        Index("ix_email_verification_expires", "expires_at"),
    )


class PromotionHistory(Base):
    """Persistent record of ML model promotion decisions.

    Stores the outcome of each training run's promotion gate so the
    admin API can serve structured, queryable promotion history without
    relying on log-file parsing.
    """

    __tablename__ = "promotion_history"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    candidate_model_version = Column(String(100), nullable=False)
    candidate_auroc = Column(Float, nullable=True)
    candidate_f1 = Column(Float, nullable=True)
    candidate_precision = Column(Float, nullable=True)
    candidate_recall = Column(Float, nullable=True)
    active_model_version = Column(String(100), nullable=True)
    active_auroc = Column(Float, nullable=True)
    promoted = Column(Boolean, nullable=False)
    reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_promotion_history_timestamp", "timestamp"),
        Index("ix_promotion_history_promoted", "promoted"),
    )


class PasswordResetToken(Base):
    """Server-side password reset token store.

    Tokens are SHA-256 hashed before storage (never stored in plaintext),
    single-use, and expire after a configurable TTL (default 30 minutes).
    The ``used_at`` field is set on consumption so a second attempt with
    the same token fails. On successful reset, all active sessions for
    the user are invalidated via the token blacklist.
    """

    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False)  # SHA-256 hex digest
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_password_reset_user_id", "user_id"),
        Index("ix_password_reset_expires", "expires_at"),
    )


class Placement(Base):
    __tablename__ = "placements"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    company_name = Column(String(100), nullable=False)
    job_title = Column(String(100), nullable=False)
    package_lpa = Column(Float, nullable=False)
    offer_date = Column(Date, nullable=False)

    student = relationship("Student", back_populates="placements")

    __table_args__ = (Index("ix_placements_student_id", "student_id"),)
