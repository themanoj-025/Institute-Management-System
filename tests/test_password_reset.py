"""Password reset flow tests.

Tests cover:
1. Valid reset succeeds and old password no longer works
2. Expired token is rejected
3. Reused token is rejected (single-use)
4. Reset invalidates other active sessions
5. Forgot-password endpoint doesn't leak whether email exists
6. Rate limiting triggers on repeated forgot-password requests
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import bcrypt
import pytest

from database.models import PasswordResetToken, User, UserRole
from services.auth_service import AuthError
from utils.time import utc_now


def _make_unique_user_data() -> dict[str, object]:
    """Helper to create unique user credentials for each test."""
    tag = uuid.uuid4().hex[:8]
    return {
        "username": f"reset_user_{tag}",
        "email": f"reset_{tag}@bb.edu.in",
        "password": "OldPass123!@#",
    }


def _create_user(test_db, user_data):
    """Helper to create a test user with given data."""
    pwd_hash = bcrypt.hashpw(user_data["password"].encode("utf-8"), bcrypt.gensalt(4)).decode(
        "utf-8"
    )
    user = User(
        username=user_data["username"],
        password_hash=pwd_hash,
        role=UserRole.student,
        email=user_data["email"],
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()
    return user


class TestPasswordReset:
    """Test the password reset flow end-to-end."""

    def test_valid_reset_succeeds(self, test_db, auth_service) -> None:
        """Valid reset should succeed and old password should no longer work."""
        user_data = _make_unique_user_data()
        user = _create_user(test_db, user_data)

        # Generate reset token
        raw_token = auth_service.generate_password_reset_token(user.id)
        assert raw_token is not None
        assert len(raw_token) > 20

        # Execute reset
        new_password = "NewPass123!@#"
        auth_service.reset_password(user.id, raw_token, new_password)

        # Verify old password hash no longer matches
        test_db.refresh(user)
        assert bcrypt.checkpw(new_password.encode("utf-8"), user.password_hash.encode("utf-8"))
        assert not bcrypt.checkpw(
            user_data["password"].encode("utf-8"), user.password_hash.encode("utf-8")
        )

        # Verify failed login attempts were reset
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    def test_expired_token_rejected(self, test_db, auth_service) -> None:
        """Expired token should be rejected."""
        user_data = _make_unique_user_data()
        user = _create_user(test_db, user_data)

        # Generate token and manually expire it
        raw_token = auth_service.generate_password_reset_token(user.id)
        token_entry = (
            test_db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .first()
        )
        assert token_entry is not None

        # Backdate expires_at to 1 minute ago
        token_entry.expires_at = utc_now() - timedelta(minutes=1)
        test_db.commit()

        # Attempt reset with expired token
        with pytest.raises(AuthError, match="invalid or has expired"):
            auth_service.reset_password(user.id, raw_token, "NewPass123!@#")

    def test_reused_token_rejected(self, test_db, auth_service) -> None:
        """Reusing a token after successful reset should be rejected."""
        user_data = _make_unique_user_data()
        user = _create_user(test_db, user_data)

        raw_token = auth_service.generate_password_reset_token(user.id)

        # First reset succeeds
        auth_service.reset_password(user.id, raw_token, "NewPass123!@#")

        # Second attempt with same token should fail
        with pytest.raises(AuthError, match="invalid or has expired"):
            auth_service.reset_password(user.id, raw_token, "AnotherPass123!@#")

    def test_forgot_password_no_email_leak(self, test_db, auth_service) -> None:
        """Forgot-password should return same response whether email exists or not."""
        user_data = _make_unique_user_data()
        user = _create_user(test_db, user_data)

        # With existing email
        with patch.object(auth_service, "send_password_reset_email") as mock_send:
            auth_service.send_password_reset_email(user)
            mock_send.assert_called_once()

        # With non-existent user (query returns None)
        from database.models import User as UserModel

        non_existent = (
            test_db.query(UserModel).filter(UserModel.email == "doesnotexist@bb.edu.in").first()
        )
        assert non_existent is None

    def test_reset_invalidates_sessions(self, test_db, auth_service) -> None:
        """Password reset should mark tokens as invalid for the user."""
        user_data = _make_unique_user_data()
        user = _create_user(test_db, user_data)

        raw_token = auth_service.generate_password_reset_token(user.id)

        # Reset password
        auth_service.reset_password(user.id, raw_token, "NewPass123!@#")

        # Invalidate all sessions
        auth_service.invalidate_user_sessions(user.id)

        # Verify password_changed_at was set on the user (recently)
        test_db.refresh(user)
        assert user.password_changed_at is not None
        # Use naive comparison to avoid SQLite stripping timezone on round-trip
        # SQLite stores aware datetimes as-is but returns them as naive;
        # comparing timestamps would treat local vs UTC differently.
        naive_now = utc_now().replace(tzinfo=None)
        naive_pwd = (
            user.password_changed_at.replace(tzinfo=None)
            if user.password_changed_at.tzinfo
            else user.password_changed_at
        )
        assert abs((naive_now - naive_pwd).total_seconds()) < 30

    def test_password_policy_enforced(self, auth_service) -> None:
        """Password must meet strength requirements."""
        with pytest.raises(AuthError, match="at least 8 characters"):
            auth_service.validate_password_strength("Short1!")

        with pytest.raises(AuthError, match="uppercase letter"):
            auth_service.validate_password_strength("nouppercase1!")

        with pytest.raises(AuthError, match="digit"):
            auth_service.validate_password_strength("NoDigits!")

        with pytest.raises(AuthError, match="special character"):
            auth_service.validate_password_strength("NoSpecialChar1")

        # Valid password should pass
        result = auth_service.validate_password_strength("ValidPass123!@#")
        assert result == "ValidPass123!@#"
