"""Tests for api.circuit_breaker — CircuitBreaker state machine."""

import asyncio

import pytest

from api.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState

pytestmark = pytest.mark.integration



class TestCircuitBreaker:
    """Test CircuitBreaker state transitions."""

    def test_initial_state(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        assert cb.state == CircuitState.CLOSED
        assert cb.is_open() is False

    def test_record_success_resets_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_open() is True

    def test_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        import time
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        import time
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        import time
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerDecorator:
    """Test the __call__ decorator."""

    @pytest.mark.asyncio
    async def test_success_passes_through(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        @cb
        async def ok_func() -> str:
            return "ok"

        result = await ok_func()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_failure_recorded(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        @cb
        async def fail_func() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await fail_func()
        assert cb._failure_count == 1

    @pytest.mark.asyncio
    async def test_open_circuit_raises(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)

        @cb
        async def fail_func() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError):
            await fail_func()
        with pytest.raises(ValueError):
            await fail_func()
        assert cb.is_open()
        with pytest.raises(CircuitBreakerOpenError):
            await fail_func()


class TestCircuitBreakerContextManager:
    """Test the __enter__/__exit__ context manager."""

    def test_success(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        with cb:
            pass
        assert cb._success_count == 1

    def test_failure(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        with pytest.raises(ValueError):
            with cb:
                raise ValueError("boom")
        assert cb._failure_count == 1

    def test_open_rejects(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)
        cb.record_failure()
        cb.record_failure()
        with pytest.raises(CircuitBreakerOpenError):
            with cb:
                pass
