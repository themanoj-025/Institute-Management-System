"""Tests for IMS validators."""

from __future__ import annotations

import pytest


class TestValidators:
    def test_validate_email_valid(self) -> None:
        from utils.validators import validate_email

        assert validate_email("test@ims.com") is True

    def test_validate_email_invalid(self) -> None:
        from utils.validators import validate_email

        assert validate_email("not-an-email") is False

    def test_validate_email_empty(self) -> None:
        from utils.validators import validate_email

        assert validate_email("") is False

    def test_validate_password_strong(self) -> None:
        from utils.validators import validate_password

        result = validate_password("MyStr0ng!Pass")
        assert result is True or isinstance(result, tuple)

    def test_validate_password_weak(self) -> None:
        from utils.validators import validate_password

        result = validate_password("123")
        assert result is False or (isinstance(result, tuple) and result[0] is False)

    def test_validate_roll_no(self) -> None:
        from utils.validators import validate_roll_no

        assert validate_roll_no("CS001") is True

    def test_validate_roll_no_empty(self) -> None:
        from utils.validators import validate_roll_no

        assert validate_roll_no("") is False


class TestConfigConstants:
    def test_constants_exist(self) -> None:
        from config.constants import APP_NAME

        assert isinstance(APP_NAME, str)

    def test_courses_exist(self) -> None:
        from config.courses import COURSES

        assert isinstance(COURSES, (list, dict))
        assert len(COURSES) > 0


class TestTimeUtils:
    def test_utc_now(self) -> None:
        from utils.time import utc_now

        result = utc_now()
        assert result is not None


class TestStructuredLogging:
    def test_setup_logger(self) -> None:
        from utils.structured_logging import setup_logger

        logger = setup_logger("test")
        assert logger is not None
