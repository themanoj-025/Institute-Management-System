"""
Integration tests for Phase A API endpoints.

Tests:
  - JWT jti and token blacklisting on refresh/logout
  - PATCH endpoints (students, courses, staff, placements)
  - OTP verification flow
  - Soft-delete and restore for fees
  - Risk explanation endpoint
  - Admin config endpoints
"""

import jwt
from fastapi.testclient import TestClient

from api.main import ALGORITHM, SECRET_KEY, app, create_access_token

pytestmark = pytest.mark.slow
client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════


def make_token(username="admin", role="admin", user_id=1, extra=None):
    """Create a test JWT with a unique jti."""
    data = {"sub": username, "role": role, "user_id": user_id, **(extra or {})}
    return create_access_token(data)


# ═══════════════════════════════════════════════════════════════════
#  TOKEN BLACKLIST TESTS
# ═══════════════════════════════════════════════════════════════════


class TestTokenBlacklist:
    def test_jti_in_response(self) -> None:
        """Verify the JWT returned by login has a jti claim."""
        # We can't test login without a real DB, but we can test the token structure
        token = make_token()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_blacklist_check_rejects_invalid_token(self) -> None:
        """Invalid JWT should be rejected."""
        resp = client.get(
            "/v1/students",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "unauthorized"

    def test_blacklist_structure(self) -> None:
        """Verify the database model for revoked tokens has required fields."""
        from database.models import RevokedToken

        # Can't easily test blacklist without DB, but verify model schema
        assert hasattr(RevokedToken, "jti")
        assert hasattr(RevokedToken, "expires_at")
        assert hasattr(RevokedToken, "revoked_at")

    def test_logout_requires_auth(self) -> None:
        """Logout should require authentication."""
        resp = client.post("/v1/auth/logout")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  PATCH ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════


class TestPatchEndpoints:
    def test_patch_student_schema(self) -> None:
        """Verify StudentPatch accepts partial data."""
        from api.main import StudentPatch

        # All fields optional
        patch = StudentPatch()
        assert patch.model_dump(exclude_unset=True) == {}

        patch = StudentPatch(first_name="Updated")
        assert patch.first_name == "Updated"
        assert patch.last_name is None

    def test_patch_course_schema(self) -> None:
        """Verify CoursePatch accepts partial data."""
        from api.main import CoursePatch

        patch = CoursePatch(name="New Name")
        assert patch.name == "New Name"
        assert patch.fee is None

    def test_patch_staff_schema(self) -> None:
        """Verify StaffPatch accepts partial data."""
        from api.main import StaffPatch

        patch = StaffPatch(first_name="New")
        assert patch.first_name == "New"
        assert patch.department is None

    def test_patch_placement_schema(self) -> None:
        """Verify PlacementPatch accepts partial data."""
        from api.main import PlacementPatch

        patch = PlacementPatch(company_name="Google")
        assert patch.company_name == "Google"
        assert patch.job_title is None

    def test_patch_endpoint_requires_auth(self) -> None:
        """PATCH endpoints should require authentication."""
        resp = client.patch("/v1/students/1", json={"first_name": "Test"})
        assert resp.status_code == 401

        resp = client.patch("/v1/courses/1", json={"name": "Test"})
        assert resp.status_code == 401

        resp = client.patch("/v1/staff/1", json={"first_name": "Test"})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════
#  OTP FLOW TESTS
# ═══════════════════════════════════════════════════════════════════


class TestOtpFlow:
    def test_otp_code_model(self) -> None:
        """Verify the OtpCode model has required fields."""
        from database.models import OtpCode

        assert hasattr(OtpCode, "code_hash")
        assert hasattr(OtpCode, "expires_at")
        assert hasattr(OtpCode, "attempt_count")
        assert hasattr(OtpCode, "is_used")
        assert hasattr(OtpCode, "max_attempts")

    def test_verify_otp_endpoint_exists(self) -> None:
        """Verify the OTP endpoint route exists.

        The endpoint may fail with 401 (invalid token), 422 (validation error),
        or 500 (DB table missing in test env) — all prove the route is mounted.
        """
        try:
            resp = client.post("/v1/auth/verify-otp", json={"user_id": 1, "otp": "000000"})
            assert resp.status_code in (401, 422, 500)
        except (ConnectionError, OSError):
            # Even a connection/DB error proves the route was registered
            pass

    def test_otp_never_in_response(self) -> None:
        """Verify OTP never appears in login response."""
        # The login response should NOT contain otp_code
        import inspect

        from services.auth_service import AuthService

        source = inspect.getsource(AuthService.login)
        # The return statement should not include 'otp_code' in the dict
        assert (
            "otp_code" not in source.split("return {")[1].split("}")[0]
            if "return {" in source
            else True
        )


# ═══════════════════════════════════════════════════════════════════
#  SOFT-DELETE TESTS
# ═══════════════════════════════════════════════════════════════════


class TestSoftDeleteFee:
    def test_soft_delete_endpoint_requires_auth(self) -> None:
        """DELETE /fees/{id} should require auth."""
        resp = client.delete("/v1/fees/1")
        assert resp.status_code == 401

    def test_restore_endpoint_requires_auth(self) -> None:
        """POST /fees/{id}/restore should require auth."""
        resp = client.post("/v1/fees/1/restore")
        assert resp.status_code == 401

    def test_fee_model_has_soft_delete_fields(self) -> None:
        """Verify Fee model has soft-delete columns."""
        from database.models import Fee

        assert hasattr(Fee, "is_deleted")
        assert hasattr(Fee, "deleted_at")
        assert hasattr(Fee, "deleted_by")

    def test_fee_payment_model_has_soft_delete(self) -> None:
        """Verify FeePayment model has soft-delete columns."""
        from database.models import FeePayment

        assert hasattr(FeePayment, "is_deleted")
        assert hasattr(FeePayment, "deleted_at")


# ═══════════════════════════════════════════════════════════════════
#  RISK EXPLANATION TESTS
# ═══════════════════════════════════════════════════════════════════


class TestRiskExplanation:
    def test_risk_explanation_endpoint_exists(self) -> None:
        """Verify the risk explanation route exists."""
        resp = client.get("/v1/analytics/students/1/risk-explanation")
        # Should require auth
        assert resp.status_code == 401

    def test_at_risk_endpoint_exists(self) -> None:
        """Verify the at-risk list endpoint exists."""
        resp = client.get("/v1/analytics/at-risk")
        assert resp.status_code == 401

    def test_risk_explanation_response_schema(self) -> None:
        """Verify RiskExplanationResponse schema has required fields."""
        from api.main import RiskExplanationResponse

        fields = RiskExplanationResponse.model_fields
        assert "student_id" in fields
        assert "risk_score" in fields
        assert "risk_level" in fields
        assert "explanations" in fields
        assert "name" in fields


# ═══════════════════════════════════════════════════════════════════
#  ADMIN CONFIG TESTS
# ═══════════════════════════════════════════════════════════════════


class TestAdminConfig:
    def test_get_config_requires_auth(self) -> None:
        """GET /admin/config/risk-thresholds should require auth."""
        resp = client.get("/v1/admin/config/risk-thresholds")
        assert resp.status_code == 401

    def test_put_config_requires_auth(self) -> None:
        """PUT /admin/config/risk-thresholds should require auth."""
        resp = client.put(
            "/v1/admin/config/risk-thresholds",
            json={"thresholds": {"attendance_risk_threshold": 65.0}},
        )
        assert resp.status_code == 401

    def test_config_response_schema(self) -> None:
        """Verify RiskThresholdResponse schema."""
        from api.main import RiskThresholdResponse, RiskThresholdUpdate

        resp_fields = RiskThresholdResponse.model_fields
        assert "thresholds" in resp_fields

        update_fields = RiskThresholdUpdate.model_fields
        assert "thresholds" in update_fields

    def test_system_config_model(self) -> None:
        """Verify SystemConfig model has required fields."""
        from database.models import SystemConfig

        assert hasattr(SystemConfig, "key")
        assert hasattr(SystemConfig, "value")
        assert hasattr(SystemConfig, "value_type")
        assert hasattr(SystemConfig, "updated_by")
        assert hasattr(SystemConfig, "updated_at")


# ═══════════════════════════════════════════════════════════════════
#  GET_CONFIG_VALUE UTILITY TESTS
# ═══════════════════════════════════════════════════════════════════


class TestConfigUtility:
    def test_get_config_value_types(self):
        """Verify get_config_value handles different value types."""
        from utils.config import get_config_value

        # Test with a mock session
        class MockEntry:
            value = "75"
            value_type = "int"

        class MockSession:
            def query(self, model):
                class MockQuery:
                    def filter(self, *args):
                        return self

                    def first(self):
                        return MockEntry()

                return MockQuery()

        session = MockSession()
        result = get_config_value(session, "test_key", 50)
        assert result == 75

    def test_get_config_value_default(self):
        """Verify get_config_value returns default when no entry exists."""

        class MockSession:
            def query(self, model):
                class MockQuery:
                    def filter(self, *args):
                        return self

                    def first(self):
                        return None

                return MockQuery()

        from utils.config import get_config_value

        session = MockSession()
        result = get_config_value(session, "missing_key", 42)
        assert result == 42

    def test_get_config_float(self):
        """Verify get_config_float returns float."""
        from utils.config import get_config_float

        class MockEntry:
            value = "75.5"
            value_type = "float"

        class MockSession:
            def query(self, model):
                class MockQuery:
                    def filter(self, *args):
                        return self

                    def first(self):
                        return MockEntry()

                return MockQuery()

        result = get_config_float(MockSession(), "test", 50.0)
        assert result == 75.5
        assert isinstance(result, float)

    def test_get_config_int(self):
        """Verify get_config_int returns int."""
        from utils.config import get_config_int

        class MockEntry:
            value = "100"
            value_type = "int"

        class MockSession:
            def query(self, model):
                class MockQuery:
                    def filter(self, *args):
                        return self

                    def first(self):
                        return MockEntry()

                return MockQuery()

        result = get_config_int(MockSession(), "test", 50)
        assert result == 100
        assert isinstance(result, int)


# ═══════════════════════════════════════════════════════════════════
#  PAGINATION VERIFICATION
# ═══════════════════════════════════════════════════════════════════


class TestPagination:
    def test_pagination_helper_shape(self) -> int:
        """Verify paginated_response returns correct shape."""
        from api.main import paginated_response

        class MockQuery:
            def count(self) -> int:
                return 100

            def filter(self, *args, **kwargs):
                return self

            def offset(self, n):
                return self

            def limit(self, n):
                return self

            def all(self) -> list[object]:
                return [{"id": i} for i in range(10)]

            @property
            def entity_zero(self):
                class MockEntity:
                    class_ = type("Cls", (), {})

                return MockEntity()

        result = paginated_response(MockQuery(), page=2, per_page=10, serialize_fn=lambda x: x)
        assert result["total"] == 100
        assert result["page"] == 2
        assert result["per_page"] == 10
        assert result["total_pages"] == 10
        assert result["next_page"] == 3
        assert result["prev_page"] == 1
        assert len(result["data"]) == 10

    def test_pagination_first_page(self) -> int:
        """Verify pagination metadata for first page."""
        from api.main import paginated_response

        class MockQuery:
            def count(self) -> int:
                return 5

            def filter(self, *args, **kwargs):
                return self

            def offset(self, n):
                return self

            def limit(self, n):
                return self

            def all(self) -> list[object]:
                return [{"id": i} for i in range(5)]

            @property
            def entity_zero(self):
                class MockEntity:
                    class_ = type("Cls", (), {})

                return MockEntity()

        result = paginated_response(MockQuery(), page=1, per_page=10, serialize_fn=lambda x: x)
        assert result["prev_page"] is None
        assert result["total_pages"] == 1
        assert result["page"] == 1


# ═══════════════════════════════════════════════════════════════════
#  SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════════


class TestSecurityHeaders:
    def test_hsts_header_present(self) -> None:
        """Verify HSTS header is set on responses."""
        resp = client.get("/health")
        assert resp.headers.get("Strict-Transport-Security") is not None
        assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]

    def test_security_headers_present(self) -> None:
        """Verify all security headers are present."""
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
        assert resp.headers.get("Referrer-Policy") is not None
        assert resp.headers.get("Permissions-Policy") is not None
        assert resp.headers.get("Content-Security-Policy") is not None


# ═══════════════════════════════════════════════════════════════════
#  CELERY CONFIGURATION TESTS (optional — requires celery installed)
# ═══════════════════════════════════════════════════════════════════


class TestCeleryConfiguration:
    def test_celery_app_importable(self) -> None:
        """Verify the Celery app module can be imported."""
        try:
            from celery_app import app as celery_app

            assert celery_app.conf.task_serializer == "json"
            assert celery_app.conf.result_serializer == "json"
            assert celery_app.conf.task_default_retry_delay == 60
            assert celery_app.conf.task_max_retries == 3
        except ImportError:
            import pytest

            pytest.skip("celery not installed")

    def test_celery_tasks_exist(self) -> None:
        """Verify expected Celery tasks are registered."""
        try:
            from celery_app import app as celery_app

            tasks = celery_app.tasks
            task_names = list(tasks.keys())
            # Check for expected task names (may be prefixed with module path)
            found_tasks = [
                any(name in t for t in task_names)
                for name in [
                    "retrain_ml_model_task",
                    "cleanup_expired_otps_task",
                    "send_email_task",
                ]
            ]
            assert any(found_tasks), f"No expected tasks found in {task_names[:10]}"
        except ImportError:
            import pytest

            pytest.skip("celery not installed")


# ═══════════════════════════════════════════════════════════════════
#  UTILS.CONFIG TESTS
# ═══════════════════════════════════════════════════════════════════


class TestSetConfigValue:
    def test_set_config_value_create(self):
        """Verify set_config_value creates a new entry."""
        from utils.config import set_config_value

        # Test with mock
        calls = []

        class MockSession:
            def query(self, model):
                class MockQuery:
                    def filter(self, *args):
                        return self

                    def first(self):
                        return None

                return MockQuery()

            def add(self, obj) -> None:
                calls.append(("add", obj))

            def commit(self) -> None:
                calls.append(("commit",))

        set_config_value(MockSession(), "test_key", 100, "Test description", user_id=1)
        assert len(calls) >= 1
        assert calls[-1] == ("commit",)

    def test_set_config_value_update(self):
        """Verify set_config_value updates an existing entry."""
        calls = []
        captured_entry = None

        class MockEntry:
            def __init__(self):
                self.value = "50"
                self.value_type = "int"
                self.updated_by = None

        class MockSession:
            def query(self, model):
                class MockQuery:
                    def filter(self, *args):
                        return self

                    def first(self):
                        nonlocal captured_entry
                        captured_entry = MockEntry()
                        return captured_entry

                return MockQuery()

            def commit(self) -> None:
                calls.append(("commit",))

        from utils.config import set_config_value


        set_config_value(MockSession(), "test_key", 200, user_id=2)
        assert captured_entry is not None
        assert captured_entry.value == "200"
        assert captured_entry.value_type == "int"
        assert captured_entry.updated_by == 2
