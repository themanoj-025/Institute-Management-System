"""Tests for audit-8 hardening: circuit breaker, task dispatcher, notifier."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from utils.time import utc_now

# ═══════════════════════════════════════════════════════════════════
#  T1 — Redis circuit breaker (api/resilience.py + api/deps.py)
# ═══════════════════════════════════════════════════════════════════


class TestRedisCircuitBreaker:
    """Unit tests for api.resilience (breaker wraps Redis, fallback safe)."""

    def test_redis_call_returns_result_on_success(self) -> None:
        from api.resilience import redis_call

        assert redis_call("op", lambda: "value", default=None) == "value"

    def test_redis_call_returns_default_on_connection_error(self) -> None:
        import redis as _redis

        from api.resilience import redis_call

        def boom() -> None:
            raise _redis.ConnectionError("connection refused")

        assert redis_call("op", boom, default="fallback") == "fallback"

    def test_redis_call_never_raises(self) -> None:
        import redis as _redis

        from api.resilience import redis_call

        def boom() -> None:
            raise _redis.ConnectionError("down")

        # Even without a default, failures must not propagate to callers.
        assert redis_call("op", boom) is None

    def test_client_is_cached_per_url(self) -> None:
        from api.resilience import get_redis_client

        c1 = get_redis_client("redis://localhost:6379/0")
        c2 = get_redis_client("redis://localhost:6379/0")
        assert c1 is c2

    def test_deps_check_blacklist_falls_back_to_db(self) -> None:
        """Redis miss (None) must fall through to the DB lookup."""
        from api.deps import check_token_blacklist

        with patch("api.resilience.redis_call", return_value=None):
            # Nonexistent jti -> DB lookup returns False, not an exception.
            assert check_token_blacklist("no-such-jti-in-db") is False

    def test_deps_blacklist_token_does_not_raise_on_redis_failure(self) -> None:
        import uuid

        from api.deps import blacklist_token

        # Unique jti: the SQLite dev DB persists between runs and jti is
        # unique — a fixed string would collide with a previous run's row.
        jti = f"jti-{uuid.uuid4()}"
        with patch("api.resilience.redis_call", side_effect=RuntimeError("boom")):
            # Must not raise even if the Redis path explodes — DB is durable.
            blacklist_token(jti, utc_now() + timedelta(hours=1), user_id=1)


# ═══════════════════════════════════════════════════════════════════
#  T2 — Sync/non-Celery dispatcher (tasks.py + celery_tasks.py)
# ═══════════════════════════════════════════════════════════════════


class TestTaskDispatcher:
    """tasks.dispatch runs inline when USE_CELERY is off."""

    def test_module_importable_without_celery(self) -> None:
        import celery_tasks  # noqa: F401

    def test_unknown_task_raises_lookup_error(self) -> None:
        import tasks

        with pytest.raises(LookupError):
            tasks.dispatch("no_such_task")

    def test_available_tasks_lists_all_names(self) -> None:
        import tasks

        names = tasks.available_tasks()
        for expected in (
            "send_email",
            "check_ml_drift",
            "retrain_ml_model",
            "cleanup_expired_otps",
            "cleanup_revoked_tokens",
            "generate_export",
        ):
            assert expected in names

    def test_sync_email_skipped_when_smtp_unconfigured(self) -> None:
        import celery_tasks

        with patch("config.settings.SMTP_HOST", ""), patch("config.settings.SMTP_USER", ""):
            result = celery_tasks.send_email_sync("a@b.c", "s", "body")
        assert result["status"] == "skipped"

    def test_dispatcher_runs_inline_when_use_celery_false(self) -> None:
        import tasks

        with (
            patch("tasks.USE_CELERY", False),
            patch("config.settings.SMTP_HOST", ""),
            patch("config.settings.SMTP_USER", ""),
        ):
            result = tasks.dispatch("send_email", "a@b.c", "s", "body")
        assert result["status"] == "skipped"

    def test_alert_marker_logged_on_email_failure(self) -> None:
        import smtplib

        import celery_tasks

        with (
            patch("config.settings.SMTP_HOST", "smtp.test"),
            patch("config.settings.SMTP_PORT", 25),
            patch("config.settings.SMTP_USER", "u"),
            patch("config.settings.SMTP_PASSWORD", "p"),
            patch("smtplib.SMTP", side_effect=smtplib.SMTPException("relay down")),
        ):
            result = celery_tasks.send_email_sync("a@b.c", "s", "body")
        assert result["status"] == "failed"
        assert "locator" in result


# ═══════════════════════════════════════════════════════════════════
#  T6 — Desktop notifier delivery status
# ═══════════════════════════════════════════════════════════════════


class TestDesktopNotifierStatus:
    """notify() must report success/failure via handle + callback."""

    def _notifier(self):
        from notifications.desktop_notifier import DesktopNotifier

        return DesktopNotifier()

    def test_success_reported_via_callback(self) -> None:

        with patch("plyer.notification.notify") as mock_notify:
            results = []
            handle = self._notifier().notify("t", "m", on_complete=results.append)
            handle.wait(timeout=5)
        assert results and results[0].status == "sent"
        mock_notify.assert_called_once()

    def test_failure_reported_via_callback(self) -> None:

        with patch("plyer.notification.notify", side_effect=OSError("no notif backend")):
            results = []
            handle = self._notifier().notify("t", "m", on_complete=results.append)
            handle.wait(timeout=5)
        assert results
        assert results[0].status == "failed"
        assert results[0].error is not None

    def test_deliver_failure_does_not_raise(self) -> None:
        from notifications.desktop_notifier import _deliver

        with patch("plyer.notification.notify", side_effect=RuntimeError("boom")):
            result = _deliver("t", "m", 5, None)
        assert result.status == "failed"

    def test_notify_failure_toasts_when_root_given(self) -> None:
        """Failure + root must schedule an error toast via root.after."""

        scheduled = []

        class FakeRoot:
            def after(self, delay, fn):
                scheduled.append(fn)

        with patch("plyer.notification.notify", side_effect=OSError("no backend")):
            handle = self._notifier().notify("t", "m", root=FakeRoot())
            handle.wait(timeout=5)
        assert scheduled, "failure toast was not scheduled on the Tk thread"
        scheduled[0]()  # executing it must not raise (toast import may fail headless)
