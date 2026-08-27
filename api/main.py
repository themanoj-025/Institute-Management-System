"""
Binary Brain Institute Management System — REST API Gateway
============================================================

Routes are versioned under `/v1/`. A future `/v2/` can be introduced by
creating a second APIRouter and including it alongside the current one.

This file is the application entry point. Route logic is split into:
  - api/schemas.py            Pydantic models, ErrorCode, pagination
  - api/deps.py               JWT helpers, auth deps, IDOR, serializers
  - api/routes/auth_routes.py Login, OTP, refresh, logout, password reset
  - api/routes/student_routes.py  Student CRUD + attendance/results bulk
  - api/routes/course_routes.py   Course CRUD
  - api/routes/staff_routes.py    Staff CRUD
  - api/routes/fee_routes.py      Fees + payment + soft-delete
  - api/routes/placement_routes.py Placements CRUD
  - api/routes/analytics_routes.py Risk explanation, analytics summary
  - api/routes/admin_routes.py    Config, risk thresholds, promotion history
"""

import os
import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from utils.time import utc_now

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger

logger = setup_logger("bb-ims-api")


# OpenAPI tag metadata

OPENAPI_TAGS = [
    {"name": "Health", "description": "Liveness probes, health checks, and Prometheus metrics."},
    {"name": "Auth", "description": "Authentication and session management."},
    {"name": "Students", "description": "Student CRUD operations."},
    {"name": "Attendance", "description": "Bulk attendance recording."},
    {"name": "Results", "description": "Bulk exam result entry."},
    {"name": "Courses", "description": "Course management."},
    {"name": "Staff", "description": "Staff member management."},
    {"name": "Fees", "description": "Fee record management."},
    {"name": "Placements", "description": "Placement and recruitment tracking."},
    {"name": "Admin", "description": "Administrative operations and ML config."},
    {"name": "Analytics", "description": "ML-powered analytics and risk assessment."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    from config.settings import init_app

    init_app()
    logger.info("App bootstrap complete")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Binary Brain Institute Management System API",
    version="1.0.0",
    description="REST API Gateway for the Binary Brain Institute Management System.",
    contact={
        "name": "Binary Brain Institute",
        "url": "https://github.com/CodeWithHardik/Institute-Management-System",
        "email": "admin@bb-edu.in",
    },
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=OPENAPI_TAGS,
)


v1_router = APIRouter(prefix="/v1", tags=[])

# CORS & Security Headers

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
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
    except (OSError, ValueError) as exc:
        logger.warning("OpenTelemetry instrumentation failed: %s", exc)

# Rate Limiting

from api.rate_limiter import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    rate_limits={
        "/v1/auth/login": (10, 60),
        "/v1/auth/refresh": (20, 60),
        "/v1/auth/otp/request": (3, 600),
        "/v1/auth/forgot-password": (3, 600),
        "/v1/auth/reset-password": (5, 600),
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
        "/v1/students?": (100, 60),
        "/v1/courses?": (100, 60),
        "/v1/staff?": (100, 60),
        "/v1/fees?": (100, 60),
        "/v1/placements?": (100, 60),
        "/v1/notices?": (100, 60),
        "/v1/analytics": (10, 60),
        "/v1/ml": (10, 60),
        "/v1/admin": (30, 60),
    },
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> None:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), interest-cohort=()"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; frame-ancestors 'none';"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ═══════════════════════════════════════════════════════════════════
#  GLOBAL EXCEPTION HANDLERS
# ═══════════════════════════════════════════════════════════════════

from api.schemas import ErrorCode, error_code_for_status


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    errors = exc.errors()
    logger.warning(f"Validation error on {request.method} {request.url.path}: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": ErrorCode.VALIDATION_ERROR.value,
                "message": "Request validation failed",
                "detail": [
                    {"field": e["loc"][-1] if e.get("loc") else "unknown", "message": e["msg"]}
                    for e in errors
                ],
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> Response:
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
#  HEALTH & METRICS (root-level, not versioned)
# ═══════════════════════════════════════════════════════════════════

from database.db_session import get_session
from utils.observability import HealthChecker

_health_checker = HealthChecker().with_db(get_session)


@app.get(
    "/health",
    summary="Root health check",
    description="Liveness probe that checks database connectivity, ML model status, and disk space.",
    tags=["Health"],
)
def health_check() -> bool:
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
    tags=["Health"],
)
def metrics() -> dict:
    from fastapi.responses import PlainTextResponse
    from utils.observability import metrics_endpoint as _metrics

    return PlainTextResponse(content=_metrics(), media_type="text/plain; version=0.0.4")


@v1_router.get(
    "/health",
    summary="Versioned health check",
    tags=["Health"],
)
def v1_health_check() -> bool:
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


# ═══════════════════════════════════════════════════════════════════
#  INCLUDE ROUTE MODULES
# ═══════════════════════════════════════════════════════════════════

from api.routes.auth_routes import router as auth_router
from api.routes.student_routes import router as student_router
from api.routes.course_routes import router as course_router
from api.routes.staff_routes import router as staff_router
from api.routes.fee_routes import router as fee_router
from api.routes.placement_routes import router as placement_router
from api.routes.analytics_routes import router as analytics_router
from api.routes.admin_routes import router as admin_router

v1_router.include_router(auth_router)
v1_router.include_router(student_router)
v1_router.include_router(course_router)
v1_router.include_router(staff_router)
v1_router.include_router(fee_router)
v1_router.include_router(placement_router)
v1_router.include_router(analytics_router)
v1_router.include_router(admin_router)

app.include_router(v1_router)
