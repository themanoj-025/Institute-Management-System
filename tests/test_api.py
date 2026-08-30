from fastapi.testclient import TestClient

from api.main import app


pytestmark = pytest.mark.slow
client = TestClient(app)


def test_login_endpoint():
    # Attempt login with non-existent user to assert standard unauthorized response
    resp = client.post("/v1/auth/login", json={"username": "none", "password": "bad"})
    assert resp.status_code == 401


def test_protected_endpoint_no_token():
    resp = client.get("/v1/students")
    assert resp.status_code == 401


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data
    assert "database" in data["checks"]
    assert "ml_model" in data["checks"]
    assert "disk" in data["checks"]
    assert "version" in data


def test_v1_health_check():
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data
    assert data["version"] == "v1"


def test_metrics_endpoint():
    """The /metrics endpoint should return Prometheus-formatted text."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "version=0.0.4" in resp.headers["content-type"]
    body = resp.text
    assert "bbims_http_requests_total" in body or "prometheus_client not installed" in body


def test_pagination_response_shape():
    # Verify the paginated response contains all required metadata keys
    resp = client.get("/v1/students", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401  # No auth = unauthorized

    # Good auth shape test via creating a JWT (must include jti for blacklist check)
    import uuid

    import jwt

    from api.main import ALGORITHM, SECRET_KEY

    token = jwt.encode(
        {
            "sub": "admin",
            "role": "admin",
            "user_id": 1,
            "exp": 9999999999,
            "jti": str(uuid.uuid4()),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    resp = client.get(
        "/v1/students?page=1&per_page=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    assert "next_page" in data
    assert "prev_page" in data
    assert "data" in data


# Rate Limiting Tests


def _make_rate_limit_app(limits=None):
    """Create a minimal app with known rate limits for testing."""
    from fastapi import FastAPI

    from api.main import v1_router
    from api.rate_limiter import RateLimitMiddleware

    if limits is None:
        limits = {
            "/v1/auth/login": (5, 60),
            "/v1/auth/refresh": (3, 60),
        }

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rate_limits=limits)
    app.include_router(v1_router)
    return app


def test_rate_limit_headers_on_protected_endpoint():
    """Protected endpoints should include X-RateLimit-* headers."""
    rl_client = TestClient(_make_rate_limit_app())
    resp = rl_client.post("/v1/auth/login", json={"username": "none", "password": "bad"})
    assert resp.status_code == 401  # not rate limited yet
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert resp.headers["X-RateLimit-Limit"] == "5"
    assert resp.headers["X-RateLimit-Remaining"] == "4"


def test_rate_limiter_rejects_excess_requests():
    """After exhausting the limit, the 6th request should get 429."""
    rl_client = TestClient(_make_rate_limit_app())

    # Send 5 allowed requests
    for _ in range(5):
        resp = rl_client.post("/v1/auth/login", json={"username": "none", "password": "bad"})
        assert resp.status_code == 401  # bad creds, not rate limited

    # 6th request should be rate-limited
    resp = rl_client.post("/v1/auth/login", json={"username": "none", "password": "bad"})
    assert resp.status_code == 429
    data = resp.json()
    assert data["error"]["code"] == "rate_limited"
    assert "Retry-After" in resp.headers
    assert resp.headers["X-RateLimit-Remaining"] == "0"


def test_rate_limiter_allows_options_preflight():
    """CORS preflight (OPTIONS) should never be rate-limited."""
    rl_client = TestClient(_make_rate_limit_app())
    # Exhaust the limit first
    for _ in range(5):
        rl_client.post("/v1/auth/login", json={"username": "none", "password": "bad"})
    # OPTIONS should still pass
    resp = rl_client.options("/v1/auth/login")
    assert resp.status_code != 429


def test_rate_limiter_no_headers_on_unprotected_endpoint():
    """Unprotected endpoints should not carry rate-limit headers."""
    rl_client = TestClient(_make_rate_limit_app())
    resp = rl_client.get("/v1/health")
    assert resp.status_code == 200
    assert "X-RateLimit-Limit" not in resp.headers


def test_rate_limiter_independent_paths():
    """Rate limits for different paths should be independent."""
    rl_client = TestClient(_make_rate_limit_app())
    # Exhaust /v1/auth/login limit
    for _ in range(5):
        rl_client.post("/v1/auth/login", json={"username": "none", "password": "bad"})
    # /v1/auth/refresh should still work (different counter)
    import uuid

    import jwt

    from api.main import ALGORITHM, SECRET_KEY


    token = jwt.encode(
        {
            "sub": "admin",
            "role": "admin",
            "user_id": 1,
            "exp": 9999999999,
            "jti": str(uuid.uuid4()),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    resp = rl_client.post(
        "/v1/auth/refresh",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["X-RateLimit-Limit"] == "3"
    assert resp.headers["X-RateLimit-Remaining"] == "2"


def test_rate_limiter_students_headers_present():
    """POST /v1/students should carry rate-limit headers.

    The rate-limit middleware runs before auth, so even an unauthenticated
    request gets counted and receives headers. Actual 429 rejection logic
    is tested via /auth/login.
    """
    rl_client = TestClient(
        _make_rate_limit_app(
            limits={
                "/v1/students": (100, 60),
            }
        )
    )
    # No auth header — request will be rejected at the auth dependency,
    # but the rate limiter runs before auth and adds headers to the response.
    resp = rl_client.post(
        "/v1/students",
        json={
            "first_name": "Test",
            "last_name": "Student",
            "email": "test_rl@example.com",
            "phone": "1111111111",
            "dob": "2000-01-01",
            "gender": "male",
            "course_id": 1,
            "session_id": 1,
        },
    )
    # Should be 401 (no auth) but still have rate-limit headers
    assert resp.status_code == 401
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
    assert resp.headers["X-RateLimit-Limit"] == "100"
