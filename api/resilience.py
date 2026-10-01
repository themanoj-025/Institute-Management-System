"""
Redis resilience helpers: circuit breaker + graceful fallback.

Before this module a hard Redis outage made every authenticated request eat a
full ``socket_connect_timeout`` while the blacklist check fell through to the
DB on every call. A shared circuit breaker trips after repeated Redis
failures so the fast DB fallback path is used immediately, and half-open
probes (after ``reset_timeout``) give Redis a chance to recover without a
restart (audit item 8.1).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, TypeVar

from redis.exceptions import RedisError

from utils.logger import setup_logger

logger = setup_logger("api.resilience", context={"service": "api", "component": "redis-resilience"})

try:
    from pybreaker import (
        CircuitBreaker,
        CircuitBreakerError,
        CircuitBreakerListener,
    )

    _PYBREAKER_AVAILABLE = True
except ImportError:  # pragma: no cover - pybreaker missing in stripped envs
    _PYBREAKER_AVAILABLE = False
    # Minimal stand-ins so the module (and the listener class below) still
    # imports when pybreaker is absent; redis_call then degrades to a plain
    # guarded call without breaker state.
    CircuitBreaker = None
    CircuitBreakerError = type("CircuitBreakerError", (Exception,), {})
    CircuitBreakerListener = object  # type: ignore[assignment,misc]

T = TypeVar("T")

# Breaker tuning: 5 consecutive Redis failures within the window open the
# circuit for 60s. Redis failures are almost always outages, not blips — the
# DB fallback is correct (durable RevokedToken rows), so tripping fast is safe.
BREAKER_FAIL_MAX = 5
BREAKER_RESET_TIMEOUT = 60.0


class _LoggingListener(CircuitBreakerListener):  # type: ignore[misc,valid-type]
    """Log breaker state transitions so ops can see Redis flap/recover."""

    def breaker_opened(self, breaker: Any) -> None:
        logger.error(
            "Redis circuit breaker OPENED after %d failures — DB fallback active for %.0fs",
            breaker.fail_counter,
            breaker.reset_timeout,
        )

    def breaker_closed(self, breaker: Any) -> None:
        logger.info("Redis circuit breaker CLOSED — Redis is healthy again")

    def breaker_half_opened(self, breaker: Any) -> None:
        logger.warning("Redis circuit breaker HALF-OPEN — probing Redis")

    def failure_raised(self, breaker: Any, exc: BaseException) -> None:
        logger.warning("Redis call failed (%d/%d): %s", breaker.fail_counter, breaker.fail_max, exc)


if _PYBREAKER_AVAILABLE:
    # Shared process-wide breaker: the open/closed state must be visible to
    # every request thread, not per-call-site (pybreaker is thread-safe).
    redis_breaker: CircuitBreaker = CircuitBreaker(  # type: ignore[misc,valid-type]
        fail_max=BREAKER_FAIL_MAX,
        reset_timeout=BREAKER_RESET_TIMEOUT,
        listeners=[_LoggingListener()],
    )
else:  # pragma: no cover
    redis_breaker = None  # type: ignore[assignment]

# redis-py clients own a connection pool and are thread-safe — cache one per
# URL instead of dialing per request.
_client_lock = threading.Lock()
_client_cache: dict[str, Any] = {}


def get_redis_client(redis_url: str) -> Any:
    """Return a cached, thread-safe redis client for ``redis_url``."""
    with _client_lock:
        client = _client_cache.get(redis_url)
        if client is None:
            import redis as _redis

            client = _redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
            _client_cache[redis_url] = client
        return client


def redis_call(op_name: str, fn: Callable[[], T], default: T | None = None) -> T | None:
    """Run a Redis operation guarded by the shared circuit breaker.

    Returns ``fn()``'s result, or ``default`` when Redis is skipped (breaker
    open), the call fails, or pybreaker is unavailable. Never raises — callers
    use the sentinel ``default`` (typically ``None`` for "not consulted") to
    decide whether to fall back to the durable DB path.
    """
    if not _PYBREAKER_AVAILABLE or redis_breaker is None:  # pragma: no cover
        try:
            return fn()
        except (ConnectionError, OSError, RedisError) as exc:
            logger.warning("Redis %s failed (pybreaker not installed): %s", op_name, exc)
            return default
    try:
        return redis_breaker.call(fn)
    except CircuitBreakerError:
        logger.warning("Redis circuit OPEN — %s skipped, using fallback", op_name)
        return default
    except (ConnectionError, OSError, RedisError) as exc:
        # Counted by the breaker (it re-raises the original exception); the
        # caller now takes the fallback path for this request.
        logger.warning("Redis %s failed: %s", op_name, exc)
        return default
