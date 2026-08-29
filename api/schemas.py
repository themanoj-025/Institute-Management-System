"""
schemas.py - Pydantic schemas, ErrorCode enum, and pagination helper.

Extracted from main.py to reduce file size and enable reuse across route modules.
"""

from enum import Enum
from math import ceil
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ═══════════════════════════════════════════════════════════════════
#  ERROR CODES
# ═══════════════════════════════════════════════════════════════════


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "validation_error"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    INTERNAL_SERVER_ERROR = "internal_server_error"


STATUS_TO_ERROR_CODE: dict[int, str] = {
    400: ErrorCode.BAD_REQUEST.value,
    401: ErrorCode.UNAUTHORIZED.value,
    403: ErrorCode.FORBIDDEN.value,
    404: ErrorCode.NOT_FOUND.value,
    405: ErrorCode.METHOD_NOT_ALLOWED.value,
    409: ErrorCode.CONFLICT.value,
    422: ErrorCode.VALIDATION_ERROR.value,
    429: ErrorCode.RATE_LIMITED.value,
    500: ErrorCode.INTERNAL_SERVER_ERROR.value,
}


def error_code_for_status(status_code: int) -> str:
    return STATUS_TO_ERROR_CODE.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR.value)


# ═══════════════════════════════════════════════════════════════════
#  PAGINATION HELPER
# ═══════════════════════════════════════════════════════════════════

MAX_PER_PAGE = 100


def paginated_response(query, page: int, per_page: int, serialize_fn, **filters) -> dict:
    per_page = max(min(per_page, MAX_PER_PAGE), 1)

    for col, val in filters.items():
        if val is not None:
            query = query.filter(getattr(query.entity_zero.class_, col) == val)

    total = query.count()
    total_pages = max(ceil(total / per_page), 0) if total > 0 else 0
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "next_page": page + 1 if page < total_pages else None,
        "prev_page": page - 1 if page > 1 else None,
        "data": [serialize_fn(r) for r in rows],
    }


# ═══════════════════════════════════════════════════════════════════
#  AUTH SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Username or email")
    password: str = Field(..., min_length=1, max_length=128, description="Account password")


class VerifyOtpRequest(BaseModel):
    user_id: int
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class VerifyOtpResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: dict


class RefreshResponse(BaseModel):
    access_token: str


class LogoutResponse(BaseModel):
    status: str
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    user_id: int
    token: str = Field(..., min_length=1, description="Password reset token from email")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


# ═══════════════════════════════════════════════════════════════════
#  STUDENT SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class StudentCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50, description="Student first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Student last name")
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15, description="Contact phone number")
    dob: str = Field(..., min_length=10, max_length=10, description="Date of birth (YYYY-MM-DD)")
    gender: str = Field(..., min_length=1, max_length=20, description="Gender (Male/Female/Other)")
    course_id: int
    session_id: int


class StudentPatch(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=50)
    last_name: str | None = Field(None, min_length=1, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=10, max_length=15)
    dob: str | None = Field(None, min_length=10, max_length=10)
    gender: str | None = Field(None, min_length=1, max_length=20)
    course_id: int | None = None
    session_id: int | None = None


class StudentResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    enrollment_no: str
    dob: str
    gender: str
    course_id: int
    session_id: int

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════
#  ATTENDANCE / RESULTS SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class AttendanceRecord(BaseModel):
    student_id: int
    subject_id: int
    session_id: int
    date: str = Field(..., min_length=10, max_length=10, description="Attendance date (YYYY-MM-DD)")
    status: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Attendance status (present/absent/late/excused)",
    )


class ResultRecord(BaseModel):
    student_id: int
    subject_id: int
    session_id: int
    exam_type: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Exam type (midterm/final/practical/assignment)",
    )
    marks_obtained: float
    total_marks: float


# ═══════════════════════════════════════════════════════════════════
#  COURSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Unique course code")
    name: str = Field(..., min_length=1, max_length=100, description="Course name")
    duration_months: int
    fee: float
    description: str | None = Field(None, max_length=1000, description="Course description")


class CoursePatch(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=100)
    duration_months: int | None = None
    fee: float | None = None
    description: str | None = Field(None, max_length=1000)


class CourseResponse(BaseModel):
    id: int
    code: str
    name: str
    duration_months: int
    fee: float
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════
#  STAFF SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class StaffCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50, description="Staff first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Staff last name")
    email: EmailStr
    phone: str | None = Field(None, min_length=10, max_length=15)
    department: str | None = Field(None, min_length=1, max_length=50)
    designation: str | None = Field(None, min_length=1, max_length=50)
    join_date: str = Field(
        ..., min_length=10, max_length=10, description="Joining date (YYYY-MM-DD)"
    )
    salary: float | None = 0.0


class StaffPatch(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=50)
    last_name: str | None = Field(None, min_length=1, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=10, max_length=15)
    department: str | None = Field(None, min_length=1, max_length=50)
    designation: str | None = Field(None, min_length=1, max_length=50)
    join_date: str | None = Field(None, min_length=10, max_length=10)
    salary: float | None = None


class StaffResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    department: str | None = None
    designation: str | None = None
    join_date: str | None = None
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════
#  FEE SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class FeeResponse(BaseModel):
    id: int
    student_name: str
    total_amount: float
    paid_amount: float
    balance: float
    due_date: str | None = None
    status: str


class PaymentCreate(BaseModel):
    fee_id: int
    amount: float
    mode: str = Field(
        "Cash",
        min_length=1,
        max_length=20,
        description="Payment mode (Cash/Card/UPI/NetBanking)",
    )
    transaction_id: str | None = Field(
        None, max_length=100, description="External transaction reference"
    )


# ═══════════════════════════════════════════════════════════════════
#  PLACEMENT SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class PlacementCreate(BaseModel):
    student_id: int
    company_name: str = Field(..., min_length=1, max_length=100, description="Company name")
    job_title: str = Field(..., min_length=1, max_length=100, description="Job title")
    package_lpa: float
    offer_date: str = Field(
        ..., min_length=10, max_length=10, description="Offer date (YYYY-MM-DD)"
    )


class PlacementPatch(BaseModel):
    company_name: str | None = Field(None, min_length=1, max_length=100)
    job_title: str | None = Field(None, min_length=1, max_length=100)
    package_lpa: float | None = None
    offer_date: str | None = Field(None, min_length=10, max_length=10)


class PlacementResponse(BaseModel):
    id: int
    student_name: str
    company_name: str
    job_title: str
    package_lpa: float
    offer_date: str


# ═══════════════════════════════════════════════════════════════════
#  ADMIN / ANALYTICS SCHEMAS
# ═══════════════════════════════════════════════════════════════════


class RiskThresholdResponse(BaseModel):
    thresholds: dict[str, Any]


class RiskThresholdUpdate(BaseModel):
    thresholds: dict[str, Any]


class RiskExplanationResponse(BaseModel):
    student_id: int
    name: str
    risk_score: float
    risk_level: str
    model: str | None = None
    model_version: str | None = None
    explanations: list[dict[str, Any]]
