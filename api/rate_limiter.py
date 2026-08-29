"""
Sliding-window rate limiter for FastAPI — in-memory by default.

Provides ``RateLimitMiddleware``, a `BaseHTTPMiddleware` that applies
configurable per-IP rate limits to specific path prefixes.  Uses a
sliding-window counter for accuracy (avoids the burst-at-boundary problem
of fixed-window approaches).

Designed for single-process deployment.  Replace ``SlidingWindowCounter``
with a Redis-backed implementation (e.g. via ``redis-py`` + sorted sets)
when scaling beyond one worker process.

Usage::

    from api.rate_limiter import RateLimitMiddleware

    app.add_middleware(
        RateLimitMiddleware,
        rate_limits={
            "/v1/auth/login":     (10, 60),   # 10 POST/min
            "/v1/auth/refresh":   (20, 60),   # 20 POST/min
            "/v1/students":       (30, 60),   # 30 POST/min
        },
    )

Rate-limit headers (RFC 6585 / standard practice):

    X-RateLimit-Limit      — max requests allowed in the window
    X-RateLimit-Remaining  — requests left in the current window
    X-RateLimit-Reset      — seconds until the window resets
    Retry-After            — seconds until the next allowed request (on 429 only)

Error code returned on 429: ``"rate_limited"`` (see ErrorCode registry
in ``api/main.py`` for the full list).
"""

import threading
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Rate-limit error code (string literal avoids circular imports)

RATE_LIMITED_ERROR_CODE = "rate_limited"

# Default rate limits
# (max_requests, window_seconds) per path prefix.
# These can be overridden via the ``rate_limits`` constructor argument.

DEFAULT_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/v1/auth/login": (10, 60),  # 10 POST/min per IP
    "/v1/auth/refresh": (20, 60),  # 20 POST/min per IP
    "/v1/students": (30, 60),  # 30 (create-student) POST/min per IP
}


# Helpers


def _client_ip(request: Request) -> str:
    """Extract the originating client IP from headers or connection."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Sliding-window counter


class SlidingWindowCounter:
    """Thread-safe, in-memory sliding-window counter for a single (path, key).

    Parameters
    ----------
    max_requests : int
        Maximum number of requests allowed within the window.
    window_seconds : int
        Duration of the sliding window in seconds.
    """

    __slots__ = ("_lock", "_store", "max_requests", "window_seconds")

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        """Remove timestamps that have fallen out of the window."""
        cutoff = now - self.window_seconds
        self._store[key] = [t for t in self._store[key] if t > cutoff]

    def allow(self, key: str) -> tuple[bool, int, float]:
        """Check whether *key* is allowed through.

        Returns
        -------
        (allowed : bool, remaining : int, reset_after : float)
            ``allowed`` is ``True`` when the request should proceed.
            ``remaining`` is the count of requests still available.
            ``reset_after`` is the number of seconds until the oldest
            window entry expires (or the full window duration if the
            key has no history yet).
        """
        now = time.time()
        with self._lock:
            self._prune(key, now)
            count = len(self._store[key])

            if count >= self.max_requests:
                oldest = self._store[key][0]
                reset_after = max(0.0, oldest + self.window_seconds - now)
                return False, 0, reset_after

            self._store[key].append(now)
            return True, self.max_requests - count - 1, float(self.window_seconds)


# Middleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces sliding-window rate limits.

    Configured via a mapping of path prefix → ``(max_requests, window_seconds)``.
    Limits apply per unique client IP address.

    OPTIONS requests (CORS preflight) are never rate-limited.

    Parameters
    ----------
    app : ASGIApp
    rate_limits : dict, optional
        Override the default rate-limit configuration.
    """

    def __init__(
        self,
        app: ASGIApp,
        rate_limits: dict[str, tuple[int, int]] | None = None,
    ):
        super().__init__(app)
        self._limits = rate_limits or DEFAULT_RATE_LIMITS.copy()
        self._counters: dict[str, SlidingWindowCounter] = {}
        self._lock = threading.Lock()

    # ── public helper for testability ───────────────────────────────

    def reset(self) -> None:
        """Clear all rate-limit state.  Intended for test teardown."""
        with self._lock:
            self._counters.clear()

    def _get_counter(self, path: str) -> SlidingWindowCounter | None:
        """Return the counter for the longest matching path prefix, or ``None``."""
        matched: str | None = None
        matched_len = 0

        for prefix in self._limits:
            if path.startswith(prefix) and len(prefix) > matched_len:
                matched = prefix
                matched_len = len(prefix)

        if matched is None:
            return None

        with self._lock:
            if matched not in self._counters:
                max_req, window = self._limits[matched]
                self._counters[matched] = SlidingWindowCounter(max_req, window)
            return self._counters[matched]

    async def dispatch(self, request: Request, call_next) -> None:
        # Never rate-limit CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        counter = self._get_counter(request.url.path)

        if counter is not None:
            ip = _client_ip(request)
            allowed, remaining, reset_after = counter.allow(ip)

            if not allowed:
                retry_after = str(int(reset_after))
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": RATE_LIMITED_ERROR_CODE,
                            "message": (
                                "You have made too many requests. "
                                "Please wait before trying again."
                            ),
                            "detail": None,
                        }
                    },
                    headers={
                        "Retry-After": retry_after,
                        "X-RateLimit-Limit": str(counter.max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": retry_after,
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(counter.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(reset_after))
            return response

        return await call_next(request)
