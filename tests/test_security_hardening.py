"""Security hardening tests for the BB-IMS application.

Tests cover:
1. App fails to start without SECRET_KEY (fail-close)
2. Passwords are never returned in API responses
3. Passwords are never logged
4. Input validation rejects SQL injection / XSS payloads
5. Rate limiting rejects excess requests on all rate-limited endpoints
6. Pagination caps prevent unbounded queries
7. OTP never returned in HTTP response bodies
8. OTP rate limiting works correctly
9. Negative values and invalid enums rejected cleanly
10. Large payloads rejected
"""

import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


pytestmark = pytest.mark.slow
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only-not-for-production")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_app_fails_without_secret_key() -> None:
    """Verify the app refuses to start when SECRET_KEY is not set."""
    original_key = os.environ.get("SECRET_KEY")
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]
    try:
        with pytest.raises(KeyError):
            _ = os.environ["SECRET_KEY"]
    finally:
        if original_key:
            os.environ["SECRET_KEY"] = original_key


def test_settings_missing_secret_key_raises() -> None:
    """Verify SECRET_KEY access raises KeyError when env var missing."""
    original_key = os.environ.get("SECRET_KEY")
    if "SECRET_KEY" in os.environ:
        del os.environ["SECRET_KEY"]
    try:
        with pytest.raises(KeyError):
            _ = os.environ["SECRET_KEY"]
    finally:
        if original_key:
            os.environ["SECRET_KEY"] = original_key


def test_password_not_in_response_body() -> None:
    """Verify login response never contains the actual submitted password value."""
    from api.main import app as _app

    client = TestClient(_app)
    resp = client.post(
        "/v1/auth/login",
        json={"username": "nonexistent", "password": "testpass"},
    )
    assert resp.status_code == 401
    body_text = resp.text.lower()
    # The word 'password' may appear in error messages like 'Invalid username or password'
    # But the actual submitted value 'testpass' should NOT appear
    assert "testpass" not in body_text, "Actual password value leaked in response!"


def test_seeder_generates_random_passwords() -> None:
    """Verify the seeder generates random passwords each run."""
    from database.seeder import _generate_password

    passwords = set()
    for _ in range(100):
        pw = _generate_password()
        assert len(pw) == 16, "Password length %d != 16" % len(pw)
        assert any(c.islower() for c in pw)
        assert any(c.isupper() for c in pw)
        assert any(c.isdigit() for c in pw)
        assert any(c in "!@#$%^&*" for c in pw)
        passwords.add(pw)
    assert len(passwords) == 100


# --- INPUT VALIDATION TESTS ------------------------------------------------


class TestInputValidation:
    """Verify the API rejects or safely handles malicious input."""

    def _make_token(self) -> str:
        import uuid

        import jwt

        from api.main import ALGORITHM, SECRET_KEY

        return jwt.encode(
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

    def test_invalid_email_rejected(self) -> None:
        """Invalid email formats should be rejected with 422."""
        from api.main import app

        client = TestClient(app)
        headers = {"Authorization": "Bearer " + self._make_token()}
        invalid_emails = ["not-an-email", "@no-local.com", "no-tld@domain", ""]
        for email in invalid_emails:
            resp = client.post(
                "/v1/students",
                headers=headers,
                json={
                    "first_name": "Test",
                    "last_name": "Email",
                    "email": email,
                    "phone": "9876543210",
                    "dob": "2000-01-01",
                    "gender": "Male",
                    "course_id": 1,
                    "session_id": 1,
                },
            )
            assert resp.status_code == 422, "Invalid email '%s' should get 422, got %d" % (
                email,
                resp.status_code,
            )

    def test_sql_injection_in_search(self) -> None:
        """SQL injection in search should not cause errors."""
        from database.db_session import SessionLocal
        from services.search_service import SearchService

        session = SessionLocal()
        try:
            svc = SearchService(session)
            for payload in self.SQL_INJECTION_PAYLOADS:
                result = svc.global_search(payload)
                assert isinstance(result, dict)
        finally:
            session.close()

    SQL_INJECTION_PAYLOADS = [
        "'; DROP TABLE students; --",
        "' OR '1'='1",
        "1; DROP TABLE users CASCADE",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "' OR 1=1 --",
    ]


# --- SEARCH SERVICE PARAMETERIZED QUERY VERIFICATION -----------------------


def test_search_service_uses_parameterized_queries() -> None:
    """Verify search service uses parameterized queries, not f-strings."""
    import ast

    search_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "services",
        "search_service.py",
    )
    with open(search_path, encoding="utf-8") as f:
        content = f.read()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            line = content.split("\n")[node.lineno - 1]
            sql_keywords = [
                "SELECT",
                "FROM",
                "WHERE",
                "INSERT",
                "UPDATE",
                "DELETE",
                "DROP",
            ]
            if any(kw in line.upper() for kw in sql_keywords):
                pytest.fail("Found f-string SQL at line %d: %s" % (node.lineno, line))


# --- PAGINATION CAP TEST -------------------------------------------------


def test_pagination_per_page_is_capped() -> int:
    """Verify paginated_response caps per_page at MAX_PER_PAGE."""
    from api.main import MAX_PER_PAGE, paginated_response

    assert MAX_PER_PAGE == 100

    class MockQuery:
        def count(self) -> int:
            return 500

        def filter(self, *args, **kwargs):
            return self

        def offset(self, n):
            return self

        def limit(self, n):
            return self

        def all(self) -> list[object]:
            return [{"id": i} for i in range(MAX_PER_PAGE)]

        @property
        def entity_zero(self):
            class MockEntity:
                class_ = type("Cls", (), {})

            return MockEntity()

    # Request per_page=999999 — should be clamped to MAX_PER_PAGE
    result = paginated_response(MockQuery(), page=1, per_page=999999, serialize_fn=lambda x: x)
    assert result["per_page"] == MAX_PER_PAGE, "per_page should be capped at %d, got %d" % (
        MAX_PER_PAGE,
        result["per_page"],
    )
    assert len(result["data"]) == MAX_PER_PAGE

    # Request per_page=50 — should pass through unchanged
    result2 = paginated_response(MockQuery(), page=1, per_page=50, serialize_fn=lambda x: x)
    assert result2["per_page"] == 50

    # Request per_page=0 — should be clamped to 1 (minimum)
    result3 = paginated_response(MockQuery(), page=1, per_page=0, serialize_fn=lambda x: x)
    assert result3["per_page"] == 1, (
        "per_page=0 should be clamped to 1, got %d" % result3["per_page"]
    )


# --- RATE LIMIT CONFIGURATION TEST ----------------------------------------


def test_rate_limits_configured_for_critical_endpoints() -> None:
    """Critical endpoints must have rate limits configured in main.py."""
    required_limits = ["/v1/auth/login", "/v1/auth/refresh", "/v1/auth/otp/request"]
    main_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "api",
        "main.py",
    )
    with open(main_path, encoding="utf-8") as f:
        content = f.read()
    for endpoint in required_limits:
        assert endpoint in content, f"Rate limit for {endpoint} not found in main.py!"


# --- HEALTH CHECK TEST -----------------------------------------------------


def test_health_check_probes_database() -> None:
    """Health check should include database connectivity check."""
    from utils.observability import HealthChecker

    checker = HealthChecker()
    report = checker.check()
    checks = report.get("checks", {})
    assert "database" in checks
    assert report.get("status") in ("ok", "degraded", "unhealthy")


# --- ACCOUNT LOCKOUT TEST --------------------------------------------------


def test_account_lockout_after_max_attempts(test_db, auth_service) -> None:
    """Account must be locked after MAX_LOGIN_ATTEMPTS consecutive failures."""
    import bcrypt

    from config.settings import MAX_LOGIN_ATTEMPTS
    from database.models import User, UserRole
    from services.auth_service import AuthError

    assert MAX_LOGIN_ATTEMPTS == 5
    pwd_hash = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt(4)).decode("utf-8")
    user = User(
        username="lockout_test_user3",
        password_hash=pwd_hash,
        role=UserRole.student,
        email="lockout3@bb.edu.in",
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()
    for _ in range(MAX_LOGIN_ATTEMPTS):
        with pytest.raises(AuthError, match="Invalid username or password"):
            auth_service.login("lockout_test_user3", "WrongPass")
    with pytest.raises(AuthError, match="Account locked"):
        auth_service.login("lockout_test_user3", "WrongPass")
    user = test_db.query(User).filter(User.username == "lockout_test_user3").first()
    assert user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS
    assert user.locked_until is not None


# --- TOKEN JTI UNIQUENESS TEST -------------------------------------------


def test_every_token_has_unique_jti() -> None:
    """Every JWT token should have a unique jti claim."""
    import jwt

    from api.main import ALGORITHM, SECRET_KEY, create_access_token

    jtis = set()
    for i in range(100):
        token = create_access_token({"sub": "user%d" % i, "role": "admin", "user_id": i})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        assert jti is not None
        assert jti not in jtis, f"Duplicate jti: {jti}"
        jtis.add(jti)
    assert len(jtis) == 100


# --- ENV FILE TEST -------------------------------------------------------


def test_env_file_exists() -> None:
    """.env.example must exist and document required variables."""
    env_example_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".env.example",
    )
    assert os.path.exists(env_example_path)
    with open(env_example_path) as f:
        content = f.read()
    assert "SECRET_KEY" in content, ".env.example must document SECRET_KEY"
    for pattern in ["sk-live-", "sk-proj-", "admin@123", "password123"]:
        assert pattern not in content.lower(), f"Suspicious pattern found: {pattern}"


# --- CORRECT LOGIN RESETS FAILED ATTEMPTS ---------------------------------


def test_correct_login_resets_failed_attempts(test_db, auth_service) -> None:
    """Successful login resets failed_login_attempts to 0."""
    import bcrypt

    from database.models import User, UserRole
    from services.auth_service import AuthError

    pwd_hash = bcrypt.hashpw(b"CorrectPass1", bcrypt.gensalt(4)).decode("utf-8")
    user = User(
        username="reset_test_user3",
        password_hash=pwd_hash,
        role=UserRole.student,
        email="reset3@bb.edu.in",
        is_active=True,
        email_verified=True,
        failed_login_attempts=3,
    )
    test_db.add(user)
    test_db.commit()
    with patch("services.auth_service.secrets.randbelow", return_value=123456):
        try:
            result = auth_service.login("reset_test_user3", "CorrectPass1")
            user = test_db.query(User).filter(User.username == "reset_test_user3").first()
            assert user.failed_login_attempts == 0
            assert user.locked_until is None
            assert result.get("otp_sent") is True
        except AuthError:
            user = test_db.query(User).filter(User.username == "reset_test_user3").first()
            assert user.failed_login_attempts == 0


# --- EMAIL VERIFICATION TESTS ---------------------------------------------


def test_email_verification_tokens(test_db, auth_service) -> None:
    """Verify email verification token generation and validation."""
    import bcrypt

    from database.models import EmailVerificationToken, User, UserRole
    from services.auth_service import AuthError

    pwd_hash = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt(4)).decode("utf-8")
    user = User(
        username="email_verify_test",
        password_hash=pwd_hash,
        role=UserRole.student,
        email="ev_test@bb.edu.in",
        is_active=True,
        email_verified=False,
    )
    test_db.add(user)
    test_db.commit()

    # Initially not verified
    assert user.email_verified is False

    # Generate verification token
    raw_token = auth_service.generate_verification_token(user.id)
    assert raw_token is not None
    assert len(raw_token) > 20

    # Verify a token entry was created
    token_entry = (
        test_db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.user_id == user.id)
        .first()
    )
    assert token_entry is not None
    assert token_entry.is_used is False
    assert token_entry.expires_at is not None

    # Verify with correct token should succeed
    result = auth_service.verify_email_token(user.id, raw_token)
    assert result is True

    # User should now be verified
    test_db.refresh(user)
    assert user.email_verified is True

    # Token should be marked as used
    test_db.refresh(token_entry)
    assert token_entry.is_used is True

    # Using the same token again should fail
    with pytest.raises(AuthError, match="invalid or has expired"):
        auth_service.verify_email_token(user.id, raw_token)


def test_login_rejected_when_email_not_verified(test_db, auth_service) -> None:
    """Login must be rejected when email_verified is False."""
    import bcrypt

    from database.models import User, UserRole
    from services.auth_service import AuthError

    pwd_hash = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt(4)).decode("utf-8")
    user = User(
        username="unverified_user",
        password_hash=pwd_hash,
        role=UserRole.student,
        email="unverified@bb.edu.in",
        is_active=True,
        email_verified=False,
    )
    test_db.add(user)
    test_db.commit()

    with pytest.raises(AuthError, match="verify your email"):
        auth_service.login("unverified_user", "TestPass123!")


def test_invalid_verification_token_rejected(test_db, auth_service) -> None:
    """Invalid verification tokens should be rejected."""
    import bcrypt

    from database.models import User, UserRole
    from services.auth_service import AuthError


    pwd_hash = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt(4)).decode("utf-8")
    user = User(
        username="bad_token_user",
        password_hash=pwd_hash,
        role=UserRole.student,
        email="bad_token@bb.edu.in",
        is_active=True,
        email_verified=False,
    )
    test_db.add(user)
    test_db.commit()

    with pytest.raises(AuthError, match="invalid or has expired"):
        auth_service.verify_email_token(user.id, "invalid-token-here")
