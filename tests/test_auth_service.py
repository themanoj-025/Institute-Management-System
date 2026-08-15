from unittest.mock import patch

from utils.time import utc_now

import bcrypt
import pytest

from database.models import User, UserRole
from services.auth_service import AuthError

PWD_ADMIN = b"TestAdminPass123!"
PWD_STAFF = b"StaffPass456!"
PWD_STUDENT = b"StudentPass789!"


def test_password_hashing(auth_service):
    # Enforce BCRYPT_COST=14
    hash_val = bcrypt.hashpw(PWD_ADMIN, bcrypt.gensalt(14)).decode("utf-8")
    assert bcrypt.checkpw(PWD_ADMIN, hash_val.encode())
    assert not bcrypt.checkpw(b"wrong", hash_val.encode())


def test_login_success(test_db, auth_service):
    # Create test user
    pwd_hash = bcrypt.hashpw(PWD_ADMIN, bcrypt.gensalt(14)).decode("utf-8")
    user = User(
        username="test_admin",
        password_hash=pwd_hash,
        role=UserRole.admin,
        email="test_admin@bb.edu.in",
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()

    result = auth_service.login("test_admin", PWD_ADMIN.decode())
    assert result["user_id"] == user.id
    assert result["role"] == "admin"
    assert result.get("otp_sent") is True


def test_login_wrong_password(auth_service):
    with pytest.raises(AuthError, match="Invalid username or password"):
        auth_service.login("test_admin", "WrongPass")


def test_login_nonexistent_user(auth_service):
    with pytest.raises(AuthError, match="Invalid username or password"):
        auth_service.login("non_existent", "SomePass")


def test_account_lockout(test_db, auth_service):
    pwd_hash = bcrypt.hashpw(PWD_STUDENT, bcrypt.gensalt(14)).decode("utf-8")
    user = User(
        username="locked_user",
        password_hash=pwd_hash,
        role=UserRole.student,
        email="locked@student.bb.edu.in",
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()

    # Attempt 5 failures
    for _ in range(5):
        try:
            auth_service.login("locked_user", "WrongPass")
        except AuthError:
            pass

    with pytest.raises(AuthError, match="Account locked"):
        auth_service.login("locked_user", "WrongPass")


def test_account_locked_timestamp(test_db, auth_service):
    user = test_db.query(User).filter(User.username == "locked_user").first()
    assert user.locked_until is not None
    # SQLite stores naive UTC datetimes. Convert both to naive for comparison
    # to avoid ``TypeError: can't compare offset-naive and offset-aware``.
    locked_until_naive = user.locked_until.replace(tzinfo=None)
    now_naive = utc_now().replace(tzinfo=None)
    assert (
        locked_until_naive > now_naive
    ), f"locked_until ({locked_until_naive}) should be after now ({now_naive})"


def test_otp_generation(auth_service):
    # Verify 6-digit OTP generation via the service
    # randbelow(900000) + 100000 => OTP "123456" when randbelow returns 23456
    with patch("services.auth_service.secrets.randbelow", return_value=23456):
        pwd_hash = bcrypt.hashpw(PWD_STAFF, bcrypt.gensalt(14)).decode("utf-8")
        user = User(
            username="otp_gen_user",
            password_hash=pwd_hash,
            role=UserRole.admin,
            email="otp_gen@bb.edu.in",
            is_active=True,
            email_verified=True,
        )
        auth_service.db.add(user)
        auth_service.db.commit()
        result = auth_service.login("otp_gen_user", PWD_STAFF.decode())
        assert result.get("otp_sent") is True


def test_otp_verification(test_db, auth_service):
    # Seed a known user for OTP verification test
    pwd_hash = bcrypt.hashpw(PWD_ADMIN, bcrypt.gensalt(14)).decode("utf-8")
    user = User(
        username="otp_admin",
        password_hash=pwd_hash,
        role=UserRole.admin,
        email="otp_admin@bb.edu.in",
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()

    # Login with a known OTP via mock: randbelow(900000)+100000 = 23456+100000 = "123456"
    with patch("services.auth_service.secrets.randbelow", return_value=23456):
        auth_service.login("otp_admin", PWD_ADMIN.decode())

    # Matching OTP should succeed and return user data
    result = auth_service.verify_otp(user.id, "123456")
    assert result["user"]["id"] == user.id
    assert result["user"]["username"] == "otp_admin"
    assert result["user"]["role"] == "admin"
    assert result["user"]["email"] == "otp_admin@bb.edu.in"
    assert result["user"]["name"] == "Administrator"

    # Generate a new OTP for mismatch test: randbelow(900000)+100000 = 899999+100000 = "999999"
    with patch("services.auth_service.secrets.randbelow", return_value=899999):
        auth_service.login("otp_admin", PWD_ADMIN.decode())

    # Mismatched OTP should raise AuthError
    with pytest.raises(AuthError, match="Invalid OTP"):
        auth_service.verify_otp(user.id, "000000")
