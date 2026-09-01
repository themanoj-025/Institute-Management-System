"""
Celery application configuration and task base class.

Task definitions are in celery_tasks.py.

Usage:
  celery -A celery_app worker --loglevel=info --concurrency=4
  celery -A celery_app beat --loglevel=info
"""

from celery import Celery, Task
from celery.schedules import crontab

from config.settings import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, IS_DEV
from utils.logger import setup_logger

logger = setup_logger("celery", context={"service": "celery", "version": "1.0"})

# Celery app

app = Celery(
    "bb_ims",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# Configuration

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_max_retries=3,
    task_soft_time_limit=300,
    task_time_limit=600,
)

# Periodic tasks (Celery Beat schedule)

if not IS_DEV:
    app.conf.beat_schedule = {
        "retrain-ml-model-weekly": {
            "task": "celery_app.retrain_ml_model_task",
            "schedule": crontab(day_of_week="monday", hour=3, minute=0),
            "options": {"queue": "ml"},
        },
        "check-ml-drift-daily": {
            "task": "celery_app.check_ml_drift_task",
            "schedule": crontab(hour=5, minute=0),
            "options": {"queue": "ml"},
        },
        "cleanup-expired-otps-hourly": {
            "task": "celery_app.cleanup_expired_otps_task",
            "schedule": crontab(minute=0),
            "options": {"queue": "maintenance"},
        },
        "cleanup-revoked-tokens-daily": {
            "task": "celery_app.cleanup_revoked_tokens_task",
            "schedule": crontab(hour=2, minute=0),
            "options": {"queue": "maintenance"},
        },
    }


# Task base class with logging


class LoggedTask(Task):
    """Base task that logs start, success, and failure."""

    def on_success(self, retval, task_id, args, kwargs) -> None:
        logger.info("Task %s succeeded", self.name, extra={"task_id": task_id})

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:
        logger.error("Task %s failed: %s", self.name, exc, extra={"task_id": task_id, "error": str(exc)})

    def on_retry(self, exc, task_id, args, kwargs, einfo) -> None:
        logger.warning("Task %s retrying: %s", self.name, exc, extra={"task_id": task_id, "error": str(exc)})
