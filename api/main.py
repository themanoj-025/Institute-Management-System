"""
Binary Brain Institute Management System — REST API Gateway
============================================================

Routes are versioned under `/v1/`. A future `/v2/` can be introduced by
creating a second APIRouter and including it alongside the current one.

Error Response Schema
---------------------
Every error follows the same shape::

    {
      "error": {
        "code": "error_code_string",
        "message": "Human-readable summary",
        "detail": null | string | list[{"field": str, "message": str}]
      }
    }

Registered error codes (see ErrorCode enum)::

    code                 | HTTP status | Meaning
    ---------------------|-------------|----------------------------------
    validation_error     | 422         | Request body failed Pydantic validation
    bad_request          | 400         | Malformed or semantically invalid request
    unauthorized         | 401         | Missing or invalid authentication
    forbidden            | 403         | Authenticated but not permitted
    not_found            | 404         | Requested resource does not exist
    method_not_allowed   | 405         | HTTP method not supported on this route
    conflict             | 409         | Resource already exists (e.g. duplicate email)
    rate_limited         | 429         | Too many requests
    internal_server_error| 500         | Unhandled server-side failure

Paginated List Response Schema
------------------------------
Every list endpoint returns::

    {
      "total": int,        # Total records matching the query
      "page": int,         # Current page (1-indexed)
      "per_page": int,     # Items per page
      "total_pages": int,  # Ceiling of total / per_page
      "next_page": int|null,   # Next page number, or null if on last page
      "prev_page": int|null,   # Previous page number, or null if on first page
      "data": [...]        # Array of items for the current page
    }
"""

import os
import sys
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import ceil
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from utils.time import utc_now

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger

logger = setup_logger("bb-ims-api")


from database.db_session import get_session
from database.models import (
    Attendance,
    Course,
    Fee,
    FeeStatus,
    Leave,
    Placement,
    PromotionHistory,
    Result,
    RevokedToken,
    Staff,
    Student,
    SystemConfig,
    User,
    UserRole,
)

# OpenAPI tag metadata

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Liveness probes, health checks, and Prometheus metrics. Do not require authentication.",
    },
    {
        "name": "Auth",
        "description": "Authentication and session management — login, token refresh, and logout.",
    },
    {
        "name": "Students",
        "description": "Student CRUD operations — list, read, create, update, patch, and delete student records.",
    },
    {
        "name": "Attendance",
        "description": "Bulk attendance recording for staff and administrators.",
    },
    {
        "name": "Results",
        "description": "Bulk exam result entry for staff and administrators.",
    },
    {
        "name": "Courses",
        "description": "Course management — create, read, update, patch, and delete courses and their associated modules/subjects.",
    },
    {
        "name": "Staff",
        "description": "Staff member management — list, read, create, update, patch, and delete faculty records.",
    },
    {
        "name": "Fees",
        "description": "Fee record management — list fees with filters, record payments, and soft-delete.",
    },
    {
        "name": "Placements",
        "description": "Placement and recruitment tracking — list, create, patch, and delete placement records.",
    },
    {
        "name": "Admin",
        "description": "Administrative operations — system configuration, risk thresholds, and restore actions.",
    },
    {
        "name": "Analytics",
        "description": "ML-powered analytics — risk assessment and student predictions.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create required directories on application startup."""
    from config.settings import init_app

    init_app()
    logger.info("App bootstrap complete")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Binary Brain Institute Management System API",
    version="1.0.0",
    description="REST API Gateway for the Binary Brain Institute Management System. "
    "Provides authenticated CRUD operations for students, courses, staff, fees, "
    "placements, attendance, and results with pagination, rate limiting, and a "
    "standardised error response format.\n\n"
    "## Authentication\n"
    "All endpoints except `/health` and `/metrics` require a Bearer JWT token "
    "obtained via `POST /v1/auth/login`. The token must be sent in the "
    "`Authorization` header as `Bearer <token>`.",
    contact={
        "name": "Binary Brain Institute",
        "url": "https://github.com/CodeWithHardik/Institute-Management-System",
        "email": "admin@bb-edu.in",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=OPENAPI_TAGS,
)


v1_router = APIRouter(
    prefix="/v1",
    tags=[],
)

# CORS & Security Headers

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5173",  # Vite dev server for web dashboard
        "http://127.0.0.1:5173",
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Metrics & Observability

from utils.observability import MetricsMiddleware

app.add_middleware(MetricsMiddleware)

from utils.observability import setup_tracing

_otel_ok = setup_tracing("bb-ims-api")
if _otel_ok:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry FastAPI instrumentation applied")
    except Exception as exc:
        logger.warning("OpenTelemetry instrumentation failed: %s", exc)

# Rate Limiting

from api.rate_limiter import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    rate_limits={
        # Authentication (existing)
        "/v1/auth/login": (10, 60),
        "/v1/auth/refresh": (20, 60),
        "/v1/auth/otp/request": (3, 600),  # 3 per 10 minutes
        "/v1/auth/forgot-password": (3, 600),  # 3 per 10 min (anti-enumeration)
        "/v1/auth/reset-password": (5, 600),  # 5 per 10 min
        # Mutating CRUD (moderate — 30/min per user)
        "/v1/students": (30, 60),
        "/v1/courses": (30, 60),
        "/v1/staff": (30, 60),
        "/v1/fees": (30, 60),
        "/v1/placements": (30, 60),
        "/v1/attendance": (30, 60),
        "/v1/results": (30, 60),
        "/v1/leaves": (30, 60),
        "/v1/notices": (30, 60),
        "/v1/feedback": (30, 60),
        # Read-heavy list endpoints (higher — 100/min per user)
        "/v1/students?": (100, 60),
        "/v1/courses?": (100, 60),
        "/v1/staff?": (100, 60),
        "/v1/fees?": (100, 60),
        "/v1/placements?": (100, 60),
        "/v1/notices?": (100, 60),
        # ML/Analytics (strict — 10/min per user)
        "/v1/analytics": (10, 60),
        "/v1/ml": (10, 60),
        # Admin operations (30/min)
        "/v1/admin": (30, 60),
    },
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), interest-cohort=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "frame-ancestors 'none';"
    )
    # HSTS enabled now that TLS termination exists (via nginx)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Configuration

SECRET_KEY = os.environ["SECRET_KEY"]  # Required — app fails to start if missing
ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

security = HTTPBearer()


# Error Code Registry


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


_STATUS_TO_ERROR_CODE: Dict[int, str] = {
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


def _error_code_for_status(status_code: int) -> str:
    return _STATUS_TO_ERROR_CODE.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR.value)


# Pagination Helper

MAX_PER_PAGE = 100  # Hard cap to prevent resource exhaustion from unbounded requests


def paginated_response(query, page: int, per_page: int, serialize_fn, **filters) -> dict:
    per_page = max(min(per_page, MAX_PER_PAGE), 1)  # Clamp: at least 1, at most MAX_PER_PAGE

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


# Global Exception Handlers


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    logger.warning(f"Validation error on {request.method} {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": "Request validation failed",
                "detail": [
                    {
                        "field": e["loc"][-1] if e.get("loc") else "unknown",
                        "message": e["msg"],
                    }
                    for e in errors
                ],
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": _error_code_for_status(exc.status_code),
                "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
                "detail": exc.detail if not isinstance(exc.detail, str) else None,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    full_tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled exception on {request.method} {request.url.path}:\n{full_tb}")

    from config.settings import IS_DEV

    detail = str(exc) if IS_DEV else "An unexpected internal server error occurred"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                "message": "An unexpected error occurred",
                "detail": detail,
            }
        },
    )


# ═══════════════════════════════════════════════════════════════════
#  PYDANTIC SCHEMAS
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


# Student Schemas


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
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    dob: Optional[str] = Field(None, min_length=10, max_length=10)
    gender: Optional[str] = Field(None, min_length=1, max_length=20)
    course_id: Optional[int] = None
    session_id: Optional[int] = None


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


# Attendance / Results


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


# Course Schemas


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, description="Unique course code")
    name: str = Field(..., min_length=1, max_length=100, description="Course name")
    duration_months: int
    fee: float
    description: Optional[str] = Field(None, max_length=1000, description="Course description")


class CoursePatch(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    duration_months: Optional[int] = None
    fee: Optional[float] = None
    description: Optional[str] = Field(None, max_length=1000)


class CourseResponse(BaseModel):
    id: int
    code: str
    name: str
    duration_months: int
    fee: float
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Staff Schemas


class StaffCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50, description="Staff first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Staff last name")
    email: EmailStr
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    department: Optional[str] = Field(None, min_length=1, max_length=50)
    designation: Optional[str] = Field(None, min_length=1, max_length=50)
    join_date: str = Field(
        ..., min_length=10, max_length=10, description="Joining date (YYYY-MM-DD)"
    )
    salary: Optional[float] = 0.0


class StaffPatch(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    department: Optional[str] = Field(None, min_length=1, max_length=50)
    designation: Optional[str] = Field(None, min_length=1, max_length=50)
    join_date: Optional[str] = Field(None, min_length=10, max_length=10)
    salary: Optional[float] = None


class StaffResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    join_date: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Fee Schemas


class FeeResponse(BaseModel):
    id: int
    student_name: str
    total_amount: float
    paid_amount: float
    balance: float
    due_date: Optional[str] = None
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
    transaction_id: Optional[str] = Field(
        None, max_length=100, description="External transaction reference"
    )


# Placement Schemas


class PlacementCreate(BaseModel):
    student_id: int
    company_name: str = Field(..., min_length=1, max_length=100, description="Company name")
    job_title: str = Field(..., min_length=1, max_length=100, description="Job title")
    package_lpa: float
    offer_date: str = Field(
        ..., min_length=10, max_length=10, description="Offer date (YYYY-MM-DD)"
    )


class PlacementPatch(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=100)
    job_title: Optional[str] = Field(None, min_length=1, max_length=100)
    package_lpa: Optional[float] = None
    offer_date: Optional[str] = Field(None, min_length=10, max_length=10)


class PlacementResponse(BaseModel):
    id: int
    student_name: str
    company_name: str
    job_title: str
    package_lpa: float
    offer_date: str


# Admin Config Schemas


class RiskThresholdResponse(BaseModel):
    thresholds: Dict[str, Any]


class RiskThresholdUpdate(BaseModel):
    thresholds: Dict[str, Any]


# Risk Explanation


class RiskExplanationResponse(BaseModel):
    student_id: int
    name: str
    risk_score: float
    risk_level: str
    model: Optional[str] = None
    model_version: Optional[str] = None
    explanations: List[Dict[str, Any]]


# ═══════════════════════════════════════════════════════════════════
#  JWT HELPERS with jti support
# ═══════════════════════════════════════════════════════════════════


def _check_token_blacklist(jti: str) -> bool:
    """Check if a JWT ID has been revoked. Returns True if blacklisted.

    Uses Redis as the primary path for O(1) lookups — if found in Redis,
    the token is blacklisted (fast path). If NOT found in Redis, always
    falls through to the DB table as the authoritative source. This
    ensures correctness even when Redis was unavailable during the
    revocation write.
    """
    # Try Redis first (fast path)
    try:
        import redis as _redis

        from config.settings import REDIS_URL

        r = _redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        if r.get(f"bl:{jti}") is not None:
            return True
    except Exception:
        pass

    # Always check DB as the authoritative source
    from database.db_session import SessionLocal

    session = SessionLocal()
    try:
        return session.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None
    finally:
        session.close()


def _blacklist_token(jti: str, expires_at: datetime, user_id: Optional[int] = None):
    """Add a token's JTI to the blacklist.

    Writes to both Redis (primary, with TTL matching token expiry) and
    the DB table (fallback for resilience against Redis data loss).
    """
    from database.db_session import SessionLocal

    # Write to Redis with TTL matching token's remaining natural expiry
    try:
        import math

        import redis as _redis

        from config.settings import REDIS_URL

        now = utc_now()
        ttl_seconds = max(1, int(math.ceil((expires_at - now).total_seconds())))
        r = _redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        r.setex(f"bl:{jti}", ttl_seconds, "1")
    except Exception as exc:
        logger.warning("Redis blacklist write failed (non-fatal): %s", exc)

    # Also write to DB table for resilience
    session = SessionLocal()
    try:
        entry = RevokedToken(
            jti=jti,
            token_type="access",
            revoked_at=utc_now(),
            expires_at=expires_at,
            user_id=user_id,
        )
        session.add(entry)
        session.commit()
    except Exception as exc:
        logger.warning("Failed to blacklist token %s: %s", jti, exc)
        session.rollback()
    finally:
        session.close()


def create_access_token(data: dict) -> str:
    """Create a JWT with a unique jti claim for blacklist support."""
    to_encode = data.copy()
    expire = utc_now() + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update(
        {
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "iat": utc_now(),
        }
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify JWT, check blacklist, check password-change revocation, and return user info."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        user_id: int = payload.get("user_id")
        jti: str = payload.get("jti")
        exp: int = payload.get("exp")
        iat: int = payload.get("iat")

        if username is None or role is None or user_id is None or jti is None:
            raise credentials_exception

        # Check token blacklist
        if _check_token_blacklist(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check password-changed-at revocation: if the user changed their
        # password after this token was issued, the token is invalid.
        if iat:
            from database.db_session import SessionLocal
            from database.models import User as UserModel

            session = SessionLocal()
            try:
                user = session.query(UserModel).filter(UserModel.id == user_id).first()
                if user and user.password_changed_at:
                    changed_ts = user.password_changed_at.timestamp()
                    if iat < changed_ts:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token has been revoked due to password change",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
            finally:
                session.close()

        return {
            "username": username,
            "role": role,
            "user_id": user_id,
            "jti": jti,
            "exp": exp,
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception


def require_role(allowed_roles: List[str]):
    """Dependency: require the authenticated user to have one of the allowed roles."""

    def dependency(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your security role privileges.",
            )
        return user

    return dependency


# IDOR Ownership Verification


def _resolve_student_user_id(resource_type: str, resource_id: int, session) -> int | None:
    """Resolve the user_id of the student who owns a given resource.

    Uses a single SQL JOIN query to find the owning student's user_id
    for any resource type that belongs to a student.
    """
    lookup = {
        "student_id": lambda rid: (
            session.query(Student.user_id).filter(Student.id == rid).scalar()
        ),
        "fee_id": lambda rid: (
            session.query(Student.user_id)
            .join(Fee, Fee.student_id == Student.id)
            .filter(Fee.id == rid)
            .scalar()
        ),
        "attendance_id": lambda rid: (
            session.query(Student.user_id)
            .join(Attendance, Attendance.student_id == Student.id)
            .filter(Attendance.id == rid)
            .scalar()
        ),
        "result_id": lambda rid: (
            session.query(Student.user_id)
            .join(Result, Result.student_id == Student.id)
            .filter(Result.id == rid)
            .scalar()
        ),
        "leave_id": lambda rid: (
            session.query(Student.user_id)
            .join(Leave, Leave.student_id == Student.id)
            .filter(Leave.id == rid)
            .scalar()
        ),
        "placement_id": lambda rid: (
            session.query(Student.user_id)
            .join(Placement, Placement.student_id == Student.id)
            .filter(Placement.id == rid)
            .scalar()
        ),
    }
    fn = lookup.get(resource_type)
    if fn is None:
        return None
    return fn(resource_id)


def verify_ownership(
    resource_type: str = "student_id",
    allow_staff: bool = True,
    allow_admin: bool = True,
):
    """FastAPI dependency that prevents Insecure Direct Object Reference (IDOR).

    Students can only access resources they own. Admins and staff bypass
    ownership checks by default.

    Usage::

        # Student can view only their own risk explanation
        @router.get("/analytics/students/{student_id}/risk-explanation",
            dependencies=[Depends(verify_ownership())])

    The dependency extracts the resource ID from the last segment of the
    URL path, resolves it through ``_resolve_student_user_id()``, and
    compares the owning student's ``user_id`` against the authenticated
    user's ``user_id``. A 403 Forbidden is raised on mismatch.

    Parameters
    ----------
    resource_type : str
        One of ``student_id``, ``fee_id``, ``attendance_id``, ``result_id``,
        ``leave_id``, ``placement_id``.
    allow_staff : bool
        Whether staff bypass ownership checks.
    allow_admin : bool
        Whether admins bypass ownership checks.
    """

    def dependency(
        request: Request,
        user: dict = Depends(get_current_user),
    ):
        if user["role"] == "admin" and allow_admin:
            return user
        if user["role"] == "staff" and allow_staff:
            return user

        # Student: extract resource ID from the last path segment
        path_parts = request.url.path.rstrip("/").split("/")
        resource_id_str = path_parts[-1] if path_parts else None
        if resource_id_str is None or not resource_id_str.isdigit():
            return user  # List endpoints without trailing ID — skip
        resource_id = int(resource_id_str)

        with get_session() as session:
            owner_user_id = _resolve_student_user_id(resource_type, resource_id, session)
            if owner_user_id is None:
                # Resource doesn't exist — let the endpoint return 404
                return user
            if owner_user_id != user["user_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this resource.",
                )

        return user

    return dependency


# Serializers


def _serialize_student(s: Student) -> dict:
    return {
        "id": s.id,
        "first_name": s.first_name,
        "last_name": s.last_name,
        "enrollment_no": s.enrollment_no,
        "course_id": s.course_id,
        "session_id": s.session_id,
    }


def _serialize_course(c: Course) -> dict:
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "duration_months": c.duration_months,
        "fee": c.fee,
        "description": c.description,
    }


def _serialize_staff(st: Staff) -> dict:
    return {
        "id": st.id,
        "first_name": st.first_name,
        "last_name": st.last_name,
        "department": st.department,
        "designation": st.designation,
        "join_date": st.join_date.isoformat() if st.join_date else None,
        "email": st.user.email if st.user else None,
    }


def _serialize_fee(f: Fee) -> dict:
    student_name = f"{f.student.first_name} {f.student.last_name}" if f.student else "\u2014"
    balance = f.total_amount - f.paid_amount - (f.scholarship_amount or 0) + (f.fine_amount or 0)
    return {
        "id": f.id,
        "student_id": f.student_id,
        "student_name": student_name,
        "total_amount": f.total_amount,
        "paid_amount": f.paid_amount,
        "balance": round(balance, 2),
        "due_date": f.due_date.isoformat() if f.due_date else None,
        "status": f.status.value if f.status else "unpaid",
        "scholarship_amount": f.scholarship_amount or 0,
        "fine_amount": f.fine_amount or 0,
    }


def _serialize_placement(p: Placement) -> dict:
    return {
        "id": p.id,
        "student_id": p.student_id,
        "student_name": (
            f"{p.student.first_name} {p.student.last_name}" if p.student else "\u2014"
        ),
        "company_name": p.company_name,
        "job_title": p.job_title,
        "package_lpa": p.package_lpa,
        "offer_date": p.offer_date.isoformat() if p.offer_date else None,
    }


# ═══════════════════════════════════════════════════════════════════
#  V1 ROUTES
# ═══════════════════════════════════════════════════════════════════


# --- Health (root + v1) ---

from utils.observability import HealthChecker

_health_checker = HealthChecker().with_db(get_session)


@app.get(
    "/health",
    summary="Root health check",
    description="Liveness probe that checks database connectivity, ML model status, and disk space.",
    response_description="Health report with per-check status and overall system health",
    tags=["Health"],
)
def health_check():
    from fastapi import status as http_status

    report = _health_checker.check()
    http_code = (
        http_status.HTTP_200_OK
        if report["status"] == "ok"
        else http_status.HTTP_503_SERVICE_UNAVAILABLE
    )
    if report["status"] == "degraded":
        http_code = http_status.HTTP_200_OK
    return JSONResponse(content=report, status_code=http_code)


@app.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Returns application metrics in Prometheus text format.",
    response_description="Prometheus-formatted metrics text",
    tags=["Health"],
)
def metrics():
    from fastapi.responses import PlainTextResponse

    from utils.observability import metrics_endpoint as _metrics

    return PlainTextResponse(content=_metrics(), media_type="text/plain; version=0.0.4")


@v1_router.get(
    "/health",
    summary="Versioned health check",
    description="Versioned health probe with identical logic to `/health`.",
    response_description="Health report with version info and per-check status",
    tags=["Health"],
)
def v1_health_check():
    from fastapi import status as http_status

    report = _health_checker.check()
    report["version"] = "v1"
    http_code = (
        http_status.HTTP_200_OK
        if report["status"] == "ok"
        else http_status.HTTP_503_SERVICE_UNAVAILABLE
    )
    if report["status"] == "degraded":
        http_code = http_status.HTTP_200_OK
    return JSONResponse(content=report, status_code=http_code)


# --- Auth ---


@v1_router.post(
    "/auth/login",
    summary="Authenticate and receive OTP",
    description="Authenticate with username and password. Returns user_id and role. "
    "A one-time password (OTP) is sent via email. The OTP MUST be verified at "
    "`/v1/auth/verify-otp` before a JWT token is issued.",
    response_description="OTP request confirmation with user_id (NO JWT - OTP verification required)",
    tags=["Auth"],
)
def login(req: LoginRequest):
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        auth_svc = AuthService(session)
        try:
            result = auth_svc.login(req.username, req.password)
        except AuthError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

        # IMPORTANT: NO JWT is issued here. The user MUST verify OTP first.
        # The token is only generated at /v1/auth/verify-otp after OTP validation.
        return {
            "status": "otp_required",
            "user_id": result["user_id"],
            "role": result["role"],
            "message": "OTP sent. Please verify at /v1/auth/verify-otp",
        }


@v1_router.post(
    "/auth/verify-otp",
    response_model=VerifyOtpResponse,
    summary="Verify OTP and get JWT",
    description="Submit the OTP received via email to complete authentication. Returns a JWT access token.",
    response_description="JWT access token with user details",
    tags=["Auth"],
)
def verify_otp(req: VerifyOtpRequest):
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        auth_svc = AuthService(session)
        try:
            result = auth_svc.verify_otp(req.user_id, req.otp)
        except AuthError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

        user_data = result["user"]
        token = create_access_token(
            {
                "sub": user_data["username"],
                "role": user_data["role"],
                "user_id": user_data["id"],
            }
        )
        return {
            "access_token": token,
            "role": user_data["role"],
            "user": user_data,
        }


@v1_router.post(
    "/auth/refresh",
    response_model=RefreshResponse,
    summary="Refresh JWT token",
    description="Issue a new JWT using an existing valid Bearer token. "
    "The old token's JTI is blacklisted, making it unusable for future requests.",
    response_description="New JWT access token (old token is invalidated)",
    tags=["Auth"],
)
def refresh_token(user: dict = Depends(get_current_user)):
    # Blacklist the old token before issuing a new one
    expires_at = (
        datetime.fromtimestamp(user["exp"], tz=timezone.utc)
        if user.get("exp")
        else (utc_now() + timedelta(hours=JWT_EXPIRE_HOURS))
    )
    _blacklist_token(user["jti"], expires_at, user["user_id"])

    token = create_access_token(
        {"sub": user["username"], "role": user["role"], "user_id": user["user_id"]}
    )
    return {"access_token": token}


@v1_router.post(
    "/auth/verify-email/send",
    summary="Send/resend email verification",
    description="Generate and send a new email verification token. The token is valid for 24 hours. "
    "Returns a confirmation message (token is NEVER in the response).",
    response_description="Verification email confirmation",
    tags=["Auth"],
)
def send_verification_email(req: VerifyOtpRequest):
    """Send verification email (resend). Uses user_id from request body."""
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        user = session.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.email_verified:
            return {
                "status": "already_verified",
                "message": "Email is already verified.",
            }

        auth_svc = AuthService(session)
        try:
            auth_svc.send_verification_email(user)
        except AuthError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return {
            "status": "sent",
            "message": "Verification email sent. Check your inbox.",
        }


@v1_router.post(
    "/auth/verify-email/confirm",
    summary="Confirm email verification with token",
    description="Submit the verification token received via email to confirm your account. "
    "The token is single-use and expires after 24 hours.",
    response_description="Verification confirmation",
    tags=["Auth"],
)
def confirm_verification(req: VerifyOtpRequest):
    """Confirm email verification with token.

    Accepts user_id and token (reusing VerifyOtpRequest schema since it has
    the same shape: user_id + token/otp).
    """
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        auth_svc = AuthService(session)
        try:
            auth_svc.verify_email_token(req.user_id, req.otp)
        except AuthError as e:
            raise HTTPException(status_code=401, detail=str(e))

        return {
            "status": "verified",
            "message": "Email verified successfully. You can now log in.",
        }


@v1_router.post(
    "/auth/logout",
    response_model=LogoutResponse,
    summary="Logout and invalidate token",
    description="Invalidate the current JWT token. The token's JTI is added to the "
    "blacklist, making it unusable for future requests even if not expired.",
    response_description="Confirmation message with blacklist status",
    tags=["Auth"],
)
def logout(user: dict = Depends(get_current_user)):
    expires_at = (
        datetime.fromtimestamp(user["exp"], tz=timezone.utc)
        if user.get("exp")
        else (utc_now() + timedelta(hours=1))
    )
    _blacklist_token(user["jti"], expires_at, user["user_id"])
    return {
        "status": "success",
        "message": "Token blacklisted. Successfully signed out.",
    }


@v1_router.post(
    "/auth/forgot-password",
    summary="Request password reset",
    description="Send a password reset link to the user's email. "
    "Always returns 200 to prevent user enumeration. The token is NEVER in the response.",
    response_description="Generic confirmation message",
    tags=["Auth"],
)
def forgot_password(req: ForgotPasswordRequest):
    """Request a password reset. Always returns 200 to prevent user enumeration."""
    from services.auth_service import AuthService

    with get_session() as session:
        user = session.query(User).filter(User.email == req.email).first()
        if user:
            auth_svc = AuthService(session)
            try:
                auth_svc.send_password_reset_email(user)
            except Exception as exc:
                logger.warning("Failed to send password reset email to %s: %s", req.email, exc)

        # Always return 200 regardless of whether the email exists
        return {
            "status": "sent",
            "message": "If an account with that email exists, a password reset link has been sent.",
        }


@v1_router.post(
    "/auth/reset-password",
    summary="Reset password with token",
    description="Submit the password reset token and new password to complete the reset. "
    "The token is single-use and expires after 30 minutes. On success, all active "
    "sessions for the user are invalidated.",
    response_description="Reset confirmation",
    tags=["Auth"],
)
def reset_password(req: ResetPasswordRequest):
    """Reset password using a valid reset token."""
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        auth_svc = AuthService(session)
        try:
            auth_svc.reset_password(req.user_id, req.token, req.new_password)
            # Invalidate all sessions after password reset
            auth_svc.invalidate_user_sessions(req.user_id)
        except AuthError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as exc:
            logger.error("Password reset failed for user %d: %s", req.user_id, exc)
            raise HTTPException(
                status_code=500,
                detail="An error occurred while resetting the password.",
            )

        return {
            "status": "reset",
            "message": "Password reset successfully. You can now log in with your new password.",
        }


# --- Student CRUD ---


@v1_router.get(
    "/students",
    summary="List students",
    description="Retrieve a paginated list of student records. Supports filtering by course_id.",
    response_description="Paginated list of students with metadata",
    tags=["Students"],
)
def get_students(
    page: int = 1,
    per_page: int = 25,
    course_id: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    with get_session() as session:
        query = session.query(Student)
        return paginated_response(query, page, per_page, _serialize_student, course_id=course_id)


@v1_router.get(
    "/students/{student_id}",
    response_model=StudentResponse,
    dependencies=[Depends(require_role(["admin", "staff"]))],
    summary="Get student by ID",
    description="Retrieve a single student record by ID. Requires admin or staff role.",
    response_description="Student record details",
    tags=["Students"],
)
def get_student(student_id: int, user: dict = Depends(get_current_user)):
    with get_session() as session:
        s = session.query(Student).filter(Student.id == student_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Student record not found")
        return s


@v1_router.post(
    "/students",
    response_model=StudentResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create student",
    description="Register a new student. Auto-generates enrollment number and secure password.",
    response_description="Created student record",
    tags=["Students"],
)
def create_student(req: StudentCreate):
    with get_session() as session:
        existing = session.query(User).filter(User.email == req.email).first()
        if existing:
            raise HTTPException(
                status_code=400, detail="Email is already registered in BB-IMS system"
            )

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


@v1_router.put(
    "/students/{student_id}",
    response_model=StudentResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Update student (full replace)",
    description="Replace an existing student record entirely with new data.",
    response_description="Updated student record",
    tags=["Students"],
)
def update_student(student_id: int, req: StudentCreate):
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


@v1_router.patch(
    "/students/{student_id}",
    response_model=StudentResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Patch student (partial update)",
    description="Update only the provided fields of a student record. Unset fields remain unchanged.",
    response_description="Updated student record",
    tags=["Students"],
)
def patch_student(student_id: int, req: StudentPatch):
    with get_session() as session:
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found")
        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "dob" and value:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            if field == "email" and value:
                # Update the associated user's email
                user = session.query(User).filter(User.id == student.user_id).first()
                if user:
                    user.email = value
            setattr(student, field, value)
        session.commit()
        return student


@v1_router.delete(
    "/students/{student_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete student",
    description="Permanently remove a student record. Cascade deletes associated attendance, fees, results, leaves, and placements.",
    response_description="Deletion confirmation",
    tags=["Students"],
)
def delete_student(student_id: int):
    with get_session() as session:
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student record not found")
        session.delete(student)
        session.commit()
        return {"status": "success", "message": "Record successfully removed."}


# --- Bulk Attendance & Results ---


@v1_router.post(
    "/attendance/bulk",
    dependencies=[Depends(require_role(["admin", "staff"]))],
    summary="Record bulk attendance",
    description="Record attendance for multiple students in a single request.",
    response_description="Confirmation with count of records entered",
    tags=["Attendance"],
)
def bulk_attendance(records: List[AttendanceRecord]):
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
        return {
            "status": "success",
            "message": f"Successfully entered {len(records)} attendance records.",
        }


@v1_router.post(
    "/results/bulk",
    dependencies=[Depends(require_role(["admin", "staff"]))],
    summary="Register bulk exam results",
    description="Register exam results for multiple students in a single request.",
    response_description="Confirmation with count of results registered",
    tags=["Results"],
)
def bulk_results(records: List[ResultRecord]):
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
        return {
            "status": "success",
            "message": f"Successfully registered {len(records)} results.",
        }


# --- Course CRUD ---


@v1_router.get(
    "/courses",
    summary="List courses",
    description="Retrieve a paginated list of all courses.",
    response_description="Paginated list of courses with metadata",
    tags=["Courses"],
)
def get_courses(
    page: int = 1,
    per_page: int = 25,
    user: dict = Depends(get_current_user),
):
    with get_session() as session:
        query = session.query(Course).order_by(Course.id)
        return paginated_response(query, page, per_page, _serialize_course)


@v1_router.get(
    "/courses/{course_id}",
    summary="Get course by ID",
    description="Retrieve a single course record with modules and subjects.",
    response_description="Course details with modules and subjects",
    tags=["Courses"],
)
def get_course(course_id: int, user: dict = Depends(get_current_user)):
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
        result = _serialize_course(c)
        result["modules"] = [{"id": m.id, "name": m.name, "order": m.order} for m in c.modules]
        result["subjects"] = [{"id": s.id, "code": s.code, "name": s.name} for s in c.subjects]
        return result


@v1_router.post(
    "/courses",
    response_model=CourseResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create course",
    description="Create a new course. Returns 409 if the course code already exists.",
    response_description="Created course record",
    tags=["Courses"],
)
def create_course(req: CourseCreate):
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


@v1_router.put(
    "/courses/{course_id}",
    response_model=CourseResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Update course (full replace)",
    description="Replace an existing course record entirely.",
    response_description="Updated course record",
    tags=["Courses"],
)
def update_course(course_id: int, req: CourseCreate):
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


@v1_router.patch(
    "/courses/{course_id}",
    response_model=CourseResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Patch course (partial update)",
    description="Update only the provided fields of a course.",
    response_description="Updated course record",
    tags=["Courses"],
)
def patch_course(course_id: int, req: CoursePatch):
    with get_session() as session:
        course = session.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(course, field, value)
        session.commit()
        return course


@v1_router.delete(
    "/courses/{course_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete course",
    description="Permanently remove a course.",
    response_description="Deletion confirmation",
    tags=["Courses"],
)
def delete_course(course_id: int):
    with get_session() as session:
        course = session.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        session.delete(course)
        session.commit()
        return {"status": "success", "message": "Course deleted."}


# --- Staff CRUD ---


@v1_router.get(
    "/staff",
    summary="List staff",
    description="Retrieve a paginated list of staff members. Supports filtering by department.",
    response_description="Paginated list of staff with metadata",
    tags=["Staff"],
)
def get_staff(
    page: int = 1,
    per_page: int = 25,
    department: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    with get_session() as session:
        from sqlalchemy.orm import joinedload

        query = session.query(Staff).options(joinedload(Staff.user))
        return paginated_response(query, page, per_page, _serialize_staff, department=department)


@v1_router.get(
    "/staff/{staff_id}",
    response_model=StaffResponse,
    summary="Get staff member by ID",
    description="Retrieve a single staff member record.",
    response_description="Staff member record",
    tags=["Staff"],
)
def get_staff_member(staff_id: int, user: dict = Depends(get_current_user)):
    with get_session() as session:
        st = session.query(Staff).filter(Staff.id == staff_id).first()
        if not st:
            raise HTTPException(status_code=404, detail="Staff record not found")
        return st


@v1_router.post(
    "/staff",
    response_model=StaffResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create staff member",
    description="Register a new staff member with auto-generated secure password.",
    response_description="Created staff record",
    tags=["Staff"],
)
def create_staff(req: StaffCreate):
    with get_session() as session:
        existing = session.query(User).filter(User.email == req.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email is already registered")

        import secrets as _secrets

        temp_password = f"Stf-{_secrets.token_hex(8)}"
        hashed = bcrypt.hashpw(temp_password.encode("utf-8"), bcrypt.gensalt(14)).decode("utf-8")
        user = User(
            username=req.email.split("@")[0],
            password_hash=hashed,
            role=UserRole.staff,
            email=req.email,
        )
        session.add(user)
        session.flush()

        staff = Staff(
            user_id=user.id,
            first_name=req.first_name,
            last_name=req.last_name,
            department=req.department,
            designation=req.designation,
            join_date=datetime.strptime(req.join_date, "%Y-%m-%d").date(),
            salary=req.salary or 0.0,
        )
        session.add(staff)
        session.commit()
        return staff


@v1_router.put(
    "/staff/{staff_id}",
    response_model=StaffResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Update staff (full replace)",
    description="Replace an existing staff member record entirely.",
    response_description="Updated staff record",
    tags=["Staff"],
)
def update_staff(staff_id: int, req: StaffCreate):
    with get_session() as session:
        staff = session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff record not found")
        staff.first_name = req.first_name
        staff.last_name = req.last_name
        staff.department = req.department
        staff.designation = req.designation
        staff.join_date = datetime.strptime(req.join_date, "%Y-%m-%d").date()
        staff.salary = req.salary or 0.0
        session.commit()
        return staff


@v1_router.patch(
    "/staff/{staff_id}",
    response_model=StaffResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Patch staff (partial update)",
    description="Update only the provided fields of a staff member.",
    response_description="Updated staff record",
    tags=["Staff"],
)
def patch_staff(staff_id: int, req: StaffPatch):
    with get_session() as session:
        staff = session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff record not found")
        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "join_date" and value:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            if field == "email" and value:
                user = session.query(User).filter(User.id == staff.user_id).first()
                if user:
                    user.email = value
            setattr(staff, field, value)
        session.commit()
        return staff


@v1_router.delete(
    "/staff/{staff_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete staff member",
    description="Permanently remove a staff member record.",
    response_description="Deletion confirmation",
    tags=["Staff"],
)
def delete_staff(staff_id: int):
    with get_session() as session:
        staff = session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff record not found")
        session.delete(staff)
        session.commit()
        return {"status": "success", "message": "Staff record deleted."}


# --- Fees (with soft-delete) ---


@v1_router.get(
    "/fees",
    summary="List fee records",
    description="Retrieve a paginated list of active (non-deleted) fee records. Supports filtering by student_id and status.",
    response_description="Paginated list of fee records with metadata",
    tags=["Fees"],
)
def get_fees(
    page: int = 1,
    per_page: int = 25,
    student_id: Optional[int] = None,
    status: Optional[str] = None,
    include_deleted: bool = False,
    user: dict = Depends(get_current_user),
):
    with get_session() as session:
        from sqlalchemy.orm import joinedload

        query = session.query(Fee).options(joinedload(Fee.student)).order_by(Fee.id.desc())

        # Soft-delete filter: exclude deleted records unless explicitly requested
        if not include_deleted:
            query = query.filter(Fee.is_deleted == False)

        # IDOR guard: students can only see their own fees
        if user["role"] == "student":
            student = session.query(Student).filter(Student.user_id == user["user_id"]).first()
            if student:
                query = query.filter(Fee.student_id == student.id)
            else:
                query = query.filter(Fee.student_id == -1)  # Return empty
        elif student_id is not None:
            query = query.filter(Fee.student_id == student_id)

        if status:
            try:
                query = query.filter(Fee.status == FeeStatus(status))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid fee status: '{status}'. Valid values: paid, partial, unpaid",
                )
        return paginated_response(query, page, per_page, _serialize_fee)


@v1_router.post(
    "/fees/payment",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Record fee payment",
    description="Record a payment against a fee record. Updates paid_amount and generates a receipt number.",
    response_description="Payment confirmation with receipt number",
    tags=["Fees"],
)
def record_payment(req: PaymentCreate):
    from services.fee_service import FeeService

    with get_session() as session:
        svc = FeeService(session)
        try:
            receipt_no = svc.record_payment(
                fee_id=req.fee_id,
                amount=req.amount,
                mode=req.mode,
                transaction_id=req.transaction_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        return {
            "status": "success",
            "message": "Payment recorded.",
            "receipt_no": receipt_no,
        }


@v1_router.delete(
    "/fees/{fee_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Soft-delete fee record",
    description="Mark a fee record as deleted (soft delete). The record is preserved in the database "
    "with is_deleted=True. Use ?permanent=true for hard delete.",
    response_description="Soft-delete confirmation",
    tags=["Fees"],
)
def delete_fee(fee_id: int, permanent: bool = False, user: dict = Depends(get_current_user)):
    with get_session() as session:
        fee = session.query(Fee).filter(Fee.id == fee_id).first()
        if not fee:
            raise HTTPException(status_code=404, detail="Fee record not found")

        if permanent:
            session.delete(fee)
        else:
            fee.is_deleted = True
            fee.deleted_at = utc_now()
            fee.deleted_by = user["user_id"]

        session.commit()
        action = "permanently deleted" if permanent else "soft-deleted"
        return {"status": "success", "message": f"Fee record {action}."}


@v1_router.post(
    "/fees/{fee_id}/restore",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Restore soft-deleted fee record",
    description="Restore a previously soft-deleted fee record by setting is_deleted=False.",
    response_description="Restore confirmation",
    tags=["Fees"],
)
def restore_fee(fee_id: int):
    with get_session() as session:
        fee = session.query(Fee).filter(Fee.id == fee_id, Fee.is_deleted).first()
        if not fee:
            raise HTTPException(status_code=404, detail="Deleted fee record not found")

        fee.is_deleted = False
        fee.deleted_at = None
        fee.deleted_by = None
        session.commit()
        return {"status": "success", "message": "Fee record restored."}


# --- Placements ---


@v1_router.get(
    "/placements",
    summary="List placements",
    description="Retrieve a paginated list of placement records.",
    response_description="Paginated list of placements with metadata",
    tags=["Placements"],
)
def get_placements(
    page: int = 1,
    per_page: int = 25,
    user: dict = Depends(get_current_user),
):
    with get_session() as session:
        from sqlalchemy.orm import joinedload

        query = (
            session.query(Placement)
            .options(joinedload(Placement.student))
            .order_by(Placement.id.desc())
        )

        # IDOR guard: students can only see their own placements
        if user["role"] == "student":
            student = session.query(Student).filter(Student.user_id == user["user_id"]).first()
            if student:
                query = query.filter(Placement.student_id == student.id)
            else:
                query = query.filter(Placement.student_id == -1)  # Return empty

        return paginated_response(query, page, per_page, _serialize_placement)


@v1_router.post(
    "/placements",
    response_model=PlacementResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create placement record",
    description="Record a new student placement.",
    response_description="Created placement record",
    tags=["Placements"],
)
def create_placement(req: PlacementCreate):
    from services.placement_service import PlacementService

    with get_session() as session:
        svc = PlacementService(session)
        placement = svc.create_placement(
            student_id=req.student_id,
            company_name=req.company_name,
            job_title=req.job_title,
            package_lpa=req.package_lpa,
            offer_date=datetime.strptime(req.offer_date, "%Y-%m-%d").date(),
        )
        return placement


@v1_router.patch(
    "/placements/{placement_id}",
    response_model=PlacementResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Patch placement (partial update)",
    description="Update only the provided fields of a placement record.",
    response_description="Updated placement record",
    tags=["Placements"],
)
def patch_placement(placement_id: int, req: PlacementPatch):
    pass

    with get_session() as session:
        placement = session.query(Placement).filter(Placement.id == placement_id).first()
        if not placement:
            raise HTTPException(status_code=404, detail="Placement not found")

        update_data = req.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "offer_date" and value:
                value = datetime.strptime(value, "%Y-%m-%d").date()
            setattr(placement, field, value)
        session.commit()

        # Return serialized placement
        return _serialize_placement(placement)


@v1_router.delete(
    "/placements/{placement_id}",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete placement",
    description="Permanently remove a placement record.",
    response_description="Deletion confirmation",
    tags=["Placements"],
)
def delete_placement(placement_id: int):
    with get_session() as session:
        placement = session.query(Placement).filter(Placement.id == placement_id).first()
        if not placement:
            raise HTTPException(status_code=404, detail="Placement not found")
        session.delete(placement)
        session.commit()
        return {"status": "success", "message": "Placement deleted."}


# --- Analytics / Risk Explanation ---


@v1_router.get(
    "/analytics/students/{student_id}/risk-explanation",
    response_model=RiskExplanationResponse,
    summary="Get student risk explanation with SHAP",
    description="Retrieve ML-powered risk assessment for a student with SHAP-based "
    "explanations of the top contributing factors.",
    response_description="Risk score with per-feature explanations",
    tags=["Analytics"],
)
def get_student_risk_explanation(
    student_id: int,
    user: dict = Depends(get_current_user),
):
    from ml.service import MLService

    with get_session() as session:
        # IDOR guard: students can only view their own risk explanation
        if user["role"] == "student":
            owner_user_id = session.query(Student.user_id).filter(Student.id == student_id).scalar()
            if owner_user_id is None or owner_user_id != user["user_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to view this student's risk data.",
                )

        # ML failure isolation: wrap ML service call in try/except
        # so an ML failure never breaks this endpoint
        try:
            svc = MLService()
            result = svc.predict_student_risk(session, student_id=student_id)
        except Exception as exc:
            logger.error("ML risk prediction failed for student %d: %s", student_id, exc)
            result = None

        if result is None:
            # Fallback: return predicted-unavailable response instead of 404
            student = session.query(Student).filter(Student.id == student_id).first()
            return {
                "student_id": student_id,
                "name": f"{student.first_name} {student.last_name}" if student else "\u2014",
                "risk_score": None,
                "risk_level": "unknown",
                "model": None,
                "model_version": None,
                "explanations": [
                    {
                        "name": "unavailable",
                        "label": "Prediction unavailable",
                        "value": 0,
                        "importance": 0,
                        "direction": "neutral",
                    }
                ],
            }
        return result


@v1_router.get(
    "/analytics/summary",
    dependencies=[Depends(require_role(["admin"]))],
    summary="Get full analytics summary with chart data",
    description="Returns attendance trends, fee breakdown, course performance, placement stats, and performance metrics "
    "for the analytics dashboard. Admin-only.",
    response_description="Complete analytics data for dashboard charts",
    tags=["Analytics"],
)
def get_analytics_summary(user: dict = Depends(get_current_user)):
    from analytics.engine import AnalyticsEngine
    from services.analytics_service import AnalyticsService

    with get_session() as session:
        engine = AnalyticsEngine(session)
        analytics_svc = AnalyticsService(session)
        summary = engine.full_summary()
        summary["course_performance"] = analytics_svc.get_course_performance_breakdown()
        return summary


@v1_router.get(
    "/analytics/at-risk",
    summary="Get at-risk students",
    description="Retrieve the top-N most at-risk students with ML-based risk scores and explanations.",
    response_description="List of at-risk students with explanations",
    tags=["Analytics"],
)
def get_at_risk_students(
    threshold: float = 0.5,
    top_n: int = 20,
    user: dict = Depends(get_current_user),
):
    from ml.service import MLService

    with get_session() as session:
        # ML failure isolation: wrap ML service call in try/except
        try:
            svc = MLService()
            results = svc.get_at_risk_students(session, threshold=threshold, top_n=top_n)
        except Exception as exc:
            logger.error("ML get_at_risk_students failed: %s", exc)
            return {
                "students": [],
                "count": 0,
                "error": "ML prediction temporarily unavailable",
            }
        return {"students": results, "count": len(results)}


# --- Admin Configuration ---


def _get_system_config_value(session, key: str, default: Any = None) -> Any:
    """Get a typed value from SystemConfig."""
    entry = session.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not entry:
        return default
    value = entry.value
    value_type = entry.value_type
    if value_type == "int":
        return int(value)
    elif value_type == "float":
        return float(value)
    elif value_type == "bool":
        return value.lower() == "true"
    return value


def _set_system_config_value(
    session, key: str, value: Any, description: str = "", user_id: Optional[int] = None
):
    """Set a typed value in SystemConfig, creating or updating as needed."""
    entry = session.query(SystemConfig).filter(SystemConfig.key == key).first()
    if isinstance(value, bool):
        value_type = "bool"
        str_value = str(value).lower()
    elif isinstance(value, int):
        value_type = "int"
        str_value = str(value)
    elif isinstance(value, float):
        value_type = "float"
        str_value = str(value)
    else:
        value_type = "string"
        str_value = str(value)

    if entry:
        entry.value = str_value
        entry.value_type = value_type
        entry.updated_by = user_id
    else:
        entry = SystemConfig(
            key=key,
            value=str_value,
            value_type=value_type,
            description=description,
            updated_by=user_id,
        )
        session.add(entry)
    session.commit()


@v1_router.get(
    "/admin/config/risk-thresholds",
    response_model=RiskThresholdResponse,
    summary="Get risk thresholds",
    description="Retrieve all admin-configurable risk thresholds used by the ML pipeline.",
    response_description="Current risk threshold values",
    tags=["Admin"],
)
def get_risk_thresholds(user: dict = Depends(require_role(["admin"]))):
    with get_session() as session:
        thresholds = {
            "attendance_risk_threshold": _get_system_config_value(
                session, "attendance_risk_threshold", 60.0
            ),
            "marks_risk_threshold": _get_system_config_value(session, "marks_risk_threshold", 40.0),
            "high_risk_threshold": _get_system_config_value(session, "high_risk_threshold", 0.7),
            "medium_risk_threshold": _get_system_config_value(
                session, "medium_risk_threshold", 0.5
            ),
            "attendance_warning_days": _get_system_config_value(
                session, "attendance_warning_days", 28
            ),
            # ── ML Drift Monitoring Status ──
            "drift_detected": _get_system_config_value(session, "drift_detected", "False"),
            "drift_severe": _get_system_config_value(session, "drift_severe", "False"),
            "drift_max_psi": _get_system_config_value(session, "drift_max_psi", "0.0"),
            "drift_max_psi_feature": _get_system_config_value(session, "drift_max_psi_feature", ""),
            "drift_features_drifted": _get_system_config_value(
                session, "drift_features_drifted", "0"
            ),
            "drift_feature_count": _get_system_config_value(session, "drift_feature_count", "0"),
            "drift_last_checked": _get_system_config_value(session, "drift_last_checked", ""),
            "drift_error": _get_system_config_value(session, "drift_error", ""),
        }
        return {"thresholds": thresholds}


@v1_router.put(
    "/admin/config/risk-thresholds",
    response_model=RiskThresholdResponse,
    summary="Update risk thresholds",
    description="Update admin-configurable risk thresholds. Only provided keys are updated.",
    response_description="Updated risk threshold values",
    tags=["Admin"],
)
def update_risk_thresholds(req: RiskThresholdUpdate, user: dict = Depends(require_role(["admin"]))):
    with get_session() as session:
        descriptions = {
            "attendance_risk_threshold": "Attendance percentage below which a student is flagged at-risk",
            "marks_risk_threshold": "Average marks percentage below which a student is flagged at-risk",
            "high_risk_threshold": "ML probability threshold for H risk classification",
            "medium_risk_threshold": "ML probability threshold for MEDIUM risk classification",
            "attendance_warning_days": "Number of days to look back for attendance warnings",
        }
        for key, value in req.thresholds.items():
            _set_system_config_value(
                session,
                key,
                value,
                description=descriptions.get(key, ""),
                user_id=user["user_id"],
            )

        # Return updated values
        thresholds = {}
        for key in descriptions:
            thresholds[key] = _get_system_config_value(
                session,
                key,
                (
                    60.0
                    if "attendance" in key
                    else (
                        40.0
                        if "marks" in key
                        else 0.7 if "high" in key else 0.5 if "medium" in key else 28
                    )
                ),
            )
        return {"thresholds": thresholds}


# --- ML Promotion History ---


@v1_router.get(
    "/admin/ml/promotion-history",
    summary="Get ML model promotion history",
    description="Retrieve a paginated list of past training runs with promotion decisions, "
    "candidate metrics, and the active model's metrics at comparison time. "
    "Admin-only.",
    response_description="Paginated list of promotion events with per-run metrics",
    tags=["Admin"],
)
def get_promotion_history(
    page: int = 1,
    per_page: int = 25,
    user: dict = Depends(require_role(["admin"])),
):
    with get_session() as session:
        query = session.query(PromotionHistory).order_by(PromotionHistory.timestamp.desc())
        total = query.count()
        total_pages = max(ceil(total / per_page), 0) if total > 0 else 0
        rows = query.offset((page - 1) * per_page).limit(per_page).all()

        def _serialize(ph: PromotionHistory) -> dict:
            return {
                "id": ph.id,
                "timestamp": ph.timestamp.isoformat() if ph.timestamp else None,
                "candidate_model_version": ph.candidate_model_version,
                "candidate_auroc": ph.candidate_auroc,
                "candidate_f1": ph.candidate_f1,
                "candidate_precision": ph.candidate_precision,
                "candidate_recall": ph.candidate_recall,
                "active_model_version": ph.active_model_version,
                "active_auroc": ph.active_auroc,
                "promoted": ph.promoted,
                "reason": ph.reason,
            }

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None,
            "data": [_serialize(r) for r in rows],
        }


# Mount the versioned router

app.include_router(v1_router)
