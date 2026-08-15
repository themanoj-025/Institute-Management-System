"""
Observability utilities for the BB-IMS application.

Provides:
  - Prometheus metrics middleware for request count, latency, and error tracking
  - Health check helper that probes DB, cache, and ML model connectivity
  - Optional OpenTelemetry tracing setup (enabled via ``OTEL_ENABLED`` env var)

Usage (api/main.py)::

    from utils.observability import MetricsMiddleware, HealthChecker, setup_tracing

    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)

    # Setup tracing (if OTEL_ENABLED=true)
    setup_tracing("bb-ims-api")
"""

import os
import time
from typing import Any, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from utils.logger import setup_logger

logger = setup_logger("observability", context={"service": "observability"})

# Prometheus Metrics (optional)
# Use a simple dict-based counter when prometheus_client is unavailable.

_metrics_enabled = False
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest

    REQUEST_COUNT = Counter(
        "bbims_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "bbims_http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    ACTIVE_REQUESTS = Gauge(
        "bbims_http_active_requests",
        "Number of in-flight HTTP requests",
    )
    DB_CONNECTION_STATUS = Gauge(
        "bbims_db_connection_status",
        "Database connection health (1=healthy, 0=unhealthy)",
    )
    _metrics_enabled = True
    logger.info("Prometheus metrics enabled")
except ImportError:
    # Prometheus client not installed — metrics will be no-ops
    logger.info("prometheus_client not available — metrics disabled")


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records Prometheus metrics for every HTTP request.

    Tracks request count (by method + endpoint + status), latency histogram,
    and active request gauge.  Safe to use when ``prometheus_client`` is not
    installed — all methods become no-ops.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not _metrics_enabled:
            return await call_next(request)

        method = request.method
        endpoint = request.url.path
        ACTIVE_REQUESTS.inc()  # type: ignore[name-defined]
        start = time.monotonic()
        response: Optional[Response] = None

        try:
            response = await call_next(request)
            return response
        finally:
            duration = time.monotonic() - start
            status = getattr(response, "status_code", 500) if response is not None else 500
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()  # type: ignore[name-defined]
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)  # type: ignore[name-defined]
            ACTIVE_REQUESTS.dec()  # type: ignore[name-defined]


def metrics_endpoint():
    """Return a plain-text response with Prometheus-formatted metrics.

    Must be registered as a FastAPI route::

        @app.get(\"/metrics\")
        def metrics():
            return Response(
                content=metrics_endpoint(),
                media_type=\"text/plain; version=0.0.4\",
            )
    """
    if not _metrics_enabled:
        return "# prometheus_client not installed — no metrics available\n"
    return generate_latest().decode("utf-8")  # type: ignore[name-defined]


# Health Checks


class HealthChecker:
    """Probe the health of backend services and return a structured report.

    Usage::

        checker = HealthChecker()
        report = checker.check()
    """

    def __init__(self):
        self._db_session_factory = None

    def with_db(self, session_factory) -> "HealthChecker":
        """Attach a SQLAlchemy session factory for DB connectivity checks."""
        self._db_session_factory = session_factory
        return self

    def check(self) -> Dict[str, Any]:
        """Run all health checks and return a dict.

        Schema::

            {
                \"status\": \"ok\" | \"degraded\" | \"unhealthy\",
                \"checks\": {
                    \"database\": {\"status\": \"ok\" | \"error\", \"detail\": str | None},
                    \"ml_model\": {\"status\": \"ok\" | \"missing\", ...},
                    \"rate_limiter\": {\"status\": \"ok\" | ...},
                    \"disk\": {\"status\": \"ok\" | ...},
                },
                \"version\": \"1.0.0\"
            }
        """
        checks: Dict[str, Dict[str, Any]] = {}
        overall = "ok"

        # Database check
        db_ok, db_detail = self._check_db()
        checks["database"] = {"status": "ok" if db_ok else "error", "detail": db_detail}
        if not db_ok:
            overall = "unhealthy"

        # ML model check
        ml_ok, ml_detail = self._check_ml()
        checks["ml_model"] = {
            "status": "ok" if ml_ok else "missing",
            "detail": ml_detail,
        }

        # Disk space check
        disk_ok, disk_detail = self._check_disk()
        checks["disk"] = {"status": "ok" if disk_ok else "warn", "detail": disk_detail}
        if not disk_ok:
            overall = "degraded" if overall == "ok" else overall

        # Update Prometheus gauge for DB status
        if _metrics_enabled:
            try:
                DB_CONNECTION_STATUS.set(1 if db_ok else 0)  # type: ignore[name-defined]
            except Exception:
                pass

        return {
            "status": overall,
            "checks": checks,
            "version": "1.0.0",
        }

    def _check_db(self) -> tuple:
        """Ping the database by executing a trivial query."""
        if not self._db_session_factory:
            return False, "No DB session factory configured"
        try:
            from sqlalchemy import text

            with self._db_session_factory() as session:
                session.execute(text("SELECT 1"))
            return True, "Connected"
        except Exception as exc:
            return False, str(exc)

    def _check_ml(self) -> tuple:
        """Check if a trained ML model exists in the registry."""
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ml",
            "models",
        )
        if not os.path.isdir(model_path):
            return False, f"Model directory not found at {model_path}"
        models = [f for f in os.listdir(model_path) if f.endswith(".json")]
        if not models:
            return False, "No trained models found"
        return True, f"{len(models)} model(s) available"

    def _check_disk(self) -> tuple:
        """Check available disk space on the logs directory (basic)."""
        try:
            import shutil

            log_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "logs",
            )
            os.makedirs(log_dir, exist_ok=True)
            usage = shutil.disk_usage(log_dir)
            free_gb = usage.free / (1024**3)
            if free_gb < 0.1:
                return False, f"Low disk space: {free_gb:.2f} GB free"
            return True, f"{free_gb:.2f} GB free"
        except Exception as exc:
            return False, str(exc)


# OpenTelemetry Tracing (optional)


def setup_tracing(service_name: str = "bb-ims-api") -> bool:
    """Initialise OpenTelemetry tracing if the ``OTEL_ENABLED`` env var is set.

    Requires ``opentelemetry-api``, ``opentelemetry-sdk``, and
    ``opentelemetry-instrumentation-fastapi`` to be installed.

    Returns ``True`` if tracing was enabled, ``False`` otherwise.
    """
    if os.getenv("OTEL_ENABLED", "").lower() not in ("1", "true", "yes"):
        logger.debug("OpenTelemetry tracing disabled (set OTEL_ENABLED=true to enable)")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry tracing enabled (endpoint=%s)", otlp_endpoint)

        # Return the provider and instrumentor for app integration
        # Caller must do: FastAPIInstrumentor.instrument_app(app)
        return True

    except ImportError as exc:
        logger.warning(
            "OpenTelemetry packages not installed — tracing disabled (%s). "
            "Install with: pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp",
            exc,
        )
        return False
    except Exception as exc:
        logger.error("Failed to initialise OpenTelemetry: %s", exc)
        return False
