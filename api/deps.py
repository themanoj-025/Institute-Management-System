"""
deps.py - Shared dependencies: JWT helpers, auth deps, IDOR protection, serializers.

Extracted from main.py to reduce file size and enable reuse across route modules.
"""

import os
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database.db_session import get_session
from database.models import (
    Attendance,
    Course,
    Fee,
    Placement,
    Result,
    RevokedToken,
    Staff,
    Student,
    User,
)

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

security = HTTPBearer()


# ═══════════════════════════════════════════════════════════════════
#  JWT HELPERS with jti support
# ═══════════════════════════════════════════════════════════════════


def check_token_blacklist(jti: str) -> bool:
    """Check if a JWT ID has been revoked."""
    try:
        import redis as _redis

        from config.settings import REDIS_URL

        r = _redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        if r.get(f"bl:{jti}") is not None:
            return True
    except (OSError, ConnectionError):
        pass

    from database.db_session import SessionLocal

    session = SessionLocal()
    try:
        return session.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None
    finally:
        session.close()


def blacklist_token(jti: str, expires_at: datetime, user_id: int | None = None) -> None:
    """Add a token's JTI to the blacklist."""
    from database.db_session import SessionLocal

    try:
        import math

        import redis as _redis

        from config.settings import REDIS_URL

        now = datetime.now(timezone.utc)
        ttl_seconds = max(1, int(math.ceil((expires_at - now).total_seconds())))
        r = _redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        r.setex(f"bl:{jti}", ttl_seconds, "1")
    except (OSError, ConnectionError):
        pass  # Redis failure must not block logout

    session = SessionLocal()
    try:
        entry = RevokedToken(
            jti=jti,
            token_type="access",
            revoked_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            user_id=user_id,
        )
        session.add(entry)
        session.commit()
    except (OSError, ConnectionError):
        session.rollback()  # DB failure during token revocation
    finally:
        session.close()


def create_access_token(data: dict) -> str:
    """Create a JWT with a unique jti claim for blacklist support."""
    from utils.time import utc_now

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


# ═══════════════════════════════════════════════════════════════════
#  AUTH DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify JWT, check blacklist, check password-change revocation."""
    from utils.time import utc_now

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

        if check_token_blacklist(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

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


def require_role(allowed_roles: list[str]) -> dict:
    """Dependency: require the authenticated user to have one of the allowed roles."""

    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your security role privileges.",
            )
        return user

    return dependency


# ═══════════════════════════════════════════════════════════════════
#  IDOR OWNERSHIP VERIFICATION
# ═══════════════════════════════════════════════════════════════════


def _resolve_student_user_id(resource_type: str, resource_id: int, session) -> int | None:
    """Resolve the user_id of the student who owns a given resource."""
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
) -> Callable:
    """FastAPI dependency that prevents IDOR."""

    def dependency(
        request: Request,
        user: dict = Depends(get_current_user),
    ):
        if user["role"] == "admin" and allow_admin:
            return user
        if user["role"] == "staff" and allow_staff:
            return user

        path_parts = request.url.path.rstrip("/").split("/")
        resource_id_str = path_parts[-1] if path_parts else None
        if resource_id_str is None or not resource_id_str.isdigit():
            return user
        resource_id = int(resource_id_str)

        with get_session() as session:
            owner_user_id = _resolve_student_user_id(resource_type, resource_id, session)
            if owner_user_id is None:
                return user
            if owner_user_id != user["user_id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this resource.",
                )

        return user

    return dependency


# ═══════════════════════════════════════════════════════════════════
#  SERIALIZERS
# ═══════════════════════════════════════════════════════════════════


def serialize_student(s: Student) -> dict:
    return {
        "id": s.id,
        "first_name": s.first_name,
        "last_name": s.last_name,
        "enrollment_no": s.enrollment_no,
        "course_id": s.course_id,
        "session_id": s.session_id,
    }


def serialize_course(c: Course) -> dict:
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "duration_months": c.duration_months,
        "fee": c.fee,
        "description": c.description,
    }


def serialize_staff(st: Staff) -> dict:
    return {
        "id": st.id,
        "first_name": st.first_name,
        "last_name": st.last_name,
        "department": st.department,
        "designation": st.designation,
        "join_date": st.join_date.isoformat() if st.join_date else None,
        "email": st.user.email if st.user else None,
    }


def serialize_fee(f: Fee) -> dict:
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


def serialize_placement(p: Placement) -> dict:
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
