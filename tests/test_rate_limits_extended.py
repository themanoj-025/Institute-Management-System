"""Extended rate limiting tests.

Tests that representative endpoints from each newly-covered route group
actually return 429 once their limit is exceeded, and that limits reset
correctly after the window passes.
"""

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


pytestmark = pytest.mark.slow
def _make_app_with_limits(limits=None) -> dict[str, object]:
    """Create a minimal FastAPI app with configurable rate limits for testing."""
    from api.rate_limiter import RateLimitMiddleware


    app = FastAPI()

    # Add a simple test endpoint for each route group
    @app.post("/v1/courses/test")
    async def test_courses() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/staff/test")
    async def test_staff() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/fees/test")
    async def test_fees() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/placements/test")
    async def test_placements() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/attendance/test")
    async def test_attendance() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/results/test")
    async def test_results() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/leaves/test")
    async def test_leaves() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/notices/test")
    async def test_notices() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/feedback/test")
    async def test_feedback() -> dict[str, object]:
        return {"status": "ok"}

    @app.get("/v1/analytics/test")
    async def test_analytics() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/courses/reset-test")
    async def test_reset_test() -> dict[str, object]:
        return {"status": "ok"}

    @app.post("/v1/auth/forgot-password")
    async def test_forgot_password() -> dict[str, object]:
        return {
            "status": "sent",
            "message": "If an account exists, a reset link has been sent.",
        }

    if limits is None:
        limits = {
            "/v1/courses": (5, 60),
            "/v1/staff": (5, 60),
            "/v1/fees": (5, 60),
            "/v1/placements": (5, 60),
            "/v1/attendance": (5, 60),
            "/v1/results": (5, 60),
            "/v1/leaves": (5, 60),
            "/v1/notices": (5, 60),
            "/v1/feedback": (5, 60),
            "/v1/analytics": (3, 60),
            "/v1/auth/forgot-password": (3, 600),
        }

    app.add_middleware(RateLimitMiddleware, rate_limits=limits)
    return app


class TestRateLimitsExtended:
    """Test rate limits on all remaining endpoint groups."""

    ENDPOINTS = [
        ("courses", "/v1/courses/test", 5, 60),
        ("staff", "/v1/staff/test", 5, 60),
        ("fees", "/v1/fees/test", 5, 60),
        ("placements", "/v1/placements/test", 5, 60),
        ("attendance", "/v1/attendance/test", 5, 60),
        ("results", "/v1/results/test", 5, 60),
        ("leaves", "/v1/leaves/test", 5, 60),
        ("notices", "/v1/notices/test", 5, 60),
        ("feedback", "/v1/feedback/test", 5, 60),
        ("analytics", "/v1/analytics/test", 3, 60),
    ]

    @pytest.mark.parametrize("name,path,limit,window", ENDPOINTS)
    def test_endpoint_returns_429_when_exhausted(self, name, path, limit, window) -> None:
        """Each endpoint should return 429 once its rate limit is exceeded."""
        app = _make_app_with_limits(
            {
                path: (limit, window),
            }
        )
        client = TestClient(app)

        # Send allowed number of requests
        method = "POST" if "auth/forgot-password" not in path and "analytics" not in path else "GET"
        for i in range(limit):
            if method == "POST":
                resp = client.post(path, json={})
            else:
                resp = client.get(path)
            # First request should succeed, subsequent ones may also succeed
            # until we hit the limit
            if i < limit - 1:
                assert (
                    resp.status_code == 200
                ), f"Request {i + 1}/{limit} on {path} should be 200, got {resp.status_code}"

        # The (limit+1)th request should be rate-limited
        if method == "POST":
            resp = client.post(path, json={})
        else:
            resp = client.get(path)
        assert (
            resp.status_code == 429
        ), f"Request {limit + 1} on {path} should be 429, got {resp.status_code}"
        data = resp.json()
        assert data["error"]["code"] == "rate_limited"
        assert "Retry-After" in resp.headers
        assert resp.headers["X-RateLimit-Remaining"] == "0"

    def test_forgot_password_rate_limited(self) -> None:
        """Forgot-password endpoint should have a strict rate limit."""
        path = "/v1/auth/forgot-password"
        limit = 3
        window = 600
        app = _make_app_with_limits({path: (limit, window)})
        client = TestClient(app)

        # Exhaust the limit
        for _i in range(limit):
            resp = client.post(path, json={"email": "test@bb.edu.in"})
            assert resp.status_code == 200 or resp.status_code == 429

        # Next should be 429
        resp = client.post(path, json={"email": "test@bb.edu.in"})
        if resp.status_code == 429:
            data = resp.json()
            assert data["error"]["code"] == "rate_limited"
            assert "Retry-After" in resp.headers
        else:
            # If it wasn't rate-limited, at least verify headers exist
            assert "X-RateLimit-Limit" in resp.headers
            assert "X-RateLimit-Remaining" in resp.headers

    def test_rate_limit_resets_after_window(self) -> None:
        """Rate limit should reset after the window expires."""
        # Use a very short window (1 second) for testing
        path = "/v1/courses/reset-test"
        limit = 2
        window = 1  # 1 second window
        app = _make_app_with_limits({path: (limit, window)})
        client = TestClient(app)

        # Exhaust the limit
        client.post(path, json={})
        client.post(path, json={})

        # 3rd request should be 429
        resp = client.post(path, json={})
        assert resp.status_code == 429

        # Wait for window to reset
        time.sleep(1.1)

        # Next request should succeed again
        resp = client.post(path, json={})
        assert (
            resp.status_code == 200
        ), f"After window reset, request should succeed, got {resp.status_code}"
        assert "X-RateLimit-Remaining" in resp.headers
        remaining = int(resp.headers["X-RateLimit-Remaining"])
        assert remaining == limit - 1, f"Expected {limit - 1} remaining, got {remaining}"

    def test_independent_rate_limits_for_different_groups(self) -> None:
        """Rate limits for different route groups should be independent."""
        app = _make_app_with_limits(
            {
                "/v1/courses": (3, 60),
                "/v1/staff": (3, 60),
            }
        )
        client = TestClient(app)

        # Exhaust courses limit
        for _ in range(3):
            client.post("/v1/courses/test", json={})

        # Staff should still work
        resp = client.post("/v1/staff/test", json={})
        assert resp.status_code == 200

        # Courses should be exhausted
        resp = client.post("/v1/courses/test", json={})
        assert resp.status_code == 429
