"""
Background task dispatcher with a sync fallback for dev/test.

Why this exists (audit item 8.2): importing ``celery_tasks`` requires the
``celery`` package, and dispatching via ``.delay()`` requires a live broker +
worker. In dev/test (or any environment without the docker-compose ``worker``
service) that breaks — so callers go through :func:`dispatch`, which runs the
same task functions inline when ``settings.USE_CELERY`` is false, keeping
celery an optional, lazy dependency.

Usage:
    import tasks
    tasks.dispatch("send_email", to_email=..., subject=..., body=...)

Task names:
    send_email, check_ml_drift, retrain_ml_model,
    cleanup_expired_otps, cleanup_revoked_tokens, generate_export
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from config.settings import USE_CELERY

logger = logging.getLogger("bb-ims.tasks")

# name -> (celery dotted path, sync dotted path). Resolved lazily so neither
# celery nor the task modules are imported until something is dispatched.
_TASK_PATHS: dict[str, tuple[str, str]] = {
    "send_email": ("celery_tasks.send_email_task", "celery_tasks.send_email_sync"),
    "check_ml_drift": ("celery_tasks.check_ml_drift_task", "celery_tasks.check_ml_drift_sync"),
    "retrain_ml_model": (
        "celery_tasks.retrain_ml_model_task",
        "celery_tasks.retrain_ml_model_sync",
    ),
    "cleanup_expired_otps": (
        "celery_tasks.cleanup_expired_otps_task",
        "celery_tasks.cleanup_expired_otps_sync",
    ),
    "cleanup_revoked_tokens": (
        "celery_tasks.cleanup_revoked_tokens_task",
        "celery_tasks.cleanup_revoked_tokens_sync",
    ),
    "generate_export": ("celery_tasks.generate_export_task", "celery_tasks.generate_export_sync"),
}


def _resolve(dotted: str) -> Callable[..., Any]:
    module_path, _, attr = dotted.rpartition(".")
    module = __import__(module_path, fromlist=[attr])
    return getattr(module, attr)


def available_tasks() -> list[str]:
    """Names accepted by :func:`dispatch`."""
    return sorted(_TASK_PATHS)


def dispatch(name: str, /, *args: Any, **kwargs: Any) -> Any:
    """Run task ``name`` via Celery, or inline when USE_CELERY is off.

    Returns the async result when dispatched to Celery, or the task's return
    value when run inline. Raises LookupError for unknown task names.
    """
    entry = _TASK_PATHS.get(name)
    if entry is None:
        raise LookupError(
            f"Unknown background task {name!r}. Available: {', '.join(sorted(_TASK_PATHS))}"
        )

    celery_path, sync_path = entry
    if not USE_CELERY:
        logger.debug("Running task %s inline (USE_CELERY is off)", name)
        return _resolve(sync_path)(*args, **kwargs)

    try:
        return _resolve(celery_path).delay(*args, **kwargs)
    except Exception as exc:  # broker connection refused, celery missing, ...
        logger.warning(
            "Celery dispatch of %r failed (%s) — falling back to inline execution", name, exc
        )
        return _resolve(sync_path)(*args, **kwargs)
