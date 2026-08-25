"""
Celery application configuration and task definitions.

Used for background/async work:
  - Email and notification sending
  - Scheduled report generation
  - Batch data exports
  - ML model retraining (periodic)

Usage:
  # Start worker:
  celery -A celery_app worker --loglevel=info --concurrency=4

  # Start beat for periodic tasks:
  celery -A celery_app beat --loglevel=info

  # Trigger a task:
  from celery_app import send_email_task
  send_email_task.delay(to="user@example.com", subject="Hello", body="...")
"""

import json
from typing import Any

from celery import Celery, Task
from celery.exceptions import MaxRetriesExceededError
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
    task_default_retry_delay=60,  # 1 minute before first retry
    task_max_retries=3,
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
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
        logger.error(
            "Task %s failed: %s",
            self.name,
            exc,
            extra={"task_id": task_id, "error": str(exc)},
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo) -> None:
        logger.warning(
            "Task %s retrying after error: %s",
            self.name,
            exc,
            extra={"task_id": task_id, "error": str(exc)},
        )


# Email / Notification Tasks


@app.task(base=LoggedTask, bind=True, max_retries=3)
def send_email_task(
    self,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
):
    """Send an email via SMTP as a background task.

    Retries with exponential backoff on failure.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    from config.settings import SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured; cannot send email to %s", to_email)
        return {"status": "skipped", "reason": "SMTP not configured"}

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject

        if html_body:
            msg.attach(MIMEText(html_body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()

        logger.info("Email sent to %s: %s", to_email, subject)
        return {"status": "sent", "to": to_email}
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        try:
            raise self.retry(exc=exc, countdown=2 ** (self.request.retries) * 60)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for email to %s", to_email)
            return {"status": "failed", "error": str(exc)}


# Shared helper: store drift report in SystemConfig


def _store_drift_report(session, report: dict) -> dict:
    """Write a drift report into SystemConfig with typed values.

    This is shared between the scheduled drift check task and the
    retrain task so the storage logic is defined exactly once.
    Returns the dict of keys written for logging / inspection.
    """
    from database.models import SystemConfig
    from utils.time import utc_now

    # Map each SystemConfig key to (value, value_type, description)
    entries = [
        (
            "drift_detected",
            str(report.get("drift_detected", False)),
            "bool",
            "Whether ML feature drift has been detected",
        ),
        (
            "drift_severe",
            str(report.get("severe_drift", False)),
            "bool",
            "Whether severe ML feature drift has been detected",
        ),
        (
            "drift_max_psi",
            str(report.get("max_psi", 0.0)),
            "float",
            "Maximum PSI across all features",
        ),
        (
            "drift_max_psi_feature",
            str(report.get("max_psi_feature", "")),
            "string",
            "Feature name with the highest PSI",
        ),
        (
            "drift_features_drifted",
            str(report.get("features_drifted", 0)),
            "int",
            "Number of features that exceeded the PSI threshold",
        ),
        (
            "drift_feature_count",
            str(report.get("feature_count", 0)),
            "int",
            "Total number of features compared",
        ),
        (
            "drift_last_checked",
            utc_now().isoformat(),
            "string",
            "ISO timestamp of the last drift check",
        ),
        (
            "drift_error",
            str(report.get("error", "")),
            "string",
            "Error message from the last drift check, if any",
        ),
    ]

    written = {}
    for key, value, value_type, description in entries:
        entry = session.query(SystemConfig).filter(SystemConfig.key == key).first()
        if entry:
            entry.value = value
            entry.value_type = value_type
        else:
            entry = SystemConfig(
                key=key,
                value=value,
                value_type=value_type,
                description=description,
            )
            session.add(entry)
        written[key] = value

    session.commit()
    return written


# ML Drift Detection Task


@app.task(base=LoggedTask, bind=True, max_retries=1)
def check_ml_drift_task(self) -> None:
    """Run drift detection on current production features vs. reference.

    Compares current feature distributions against the reference
    distributions saved at training time using PSI (Population Stability
    Index). Results are stored in SystemConfig so they can be surfaced
    in the admin dashboard.

    Called daily by Celery Beat.
    """
    try:
        from database.db_session import SessionLocal
        from ml.drift import compute_drift_report

        session = SessionLocal()
        try:
            report = compute_drift_report(session)
            _store_drift_report(session, report)

            if report.get("drift_detected"):
                logger.warning(
                    "ML drift detected! %d/%d features drifted. Max PSI=%.4f on '%s'",
                    report.get("features_drifted", 0),
                    report.get("feature_count", 0),
                    report.get("max_psi", 0.0),
                    report.get("max_psi_feature", ""),
                )
            else:
                logger.info(
                    "ML drift check passed. Max PSI=%.4f (threshold=%.2f)",
                    report.get("max_psi", 0.0),
                    0.10,
                )

            return {"status": "ok", "drift_detected": report.get("drift_detected")}
        finally:
            session.close()
    except Exception as exc:
        logger.error("ML drift check failed: %s", exc)
        try:
            raise self.retry(exc=exc, countdown=300)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


# ML Model Retraining Task


@app.task(base=LoggedTask, bind=True, max_retries=2)
def retrain_ml_model_task(self, force: bool = False) -> None:
    """Retrain the ML risk prediction model and log metrics.

    Called weekly by Celery Beat, or on-demand via admin UI.
    """
    try:
        from database.db_session import SessionLocal
        from ml.drift import compute_drift_report
        from ml.service import MLService

        session = SessionLocal()
        try:
            svc = MLService()
            trained, metrics = svc.train(session, force=force)
            if trained:
                logger.info("ML model retrained: %s", json.dumps(metrics))
                # After retraining, reference distributions were saved by train_risk_model.
                # Run drift check against the new reference to establish a baseline.
                try:
                    drift_report = compute_drift_report(session)
                    logger.info(
                        "Post-retrain drift baseline: max_psi=%.4f, features=%d",
                        drift_report.get("max_psi", 0.0),
                        drift_report.get("feature_count", 0),
                    )
                except Exception as drift_err:
                    logger.warning("Post-retrain drift baseline failed (non-fatal): %s", drift_err)
            else:
                logger.info("ML model retrain skipped: %s", metrics)
                # If not retrained but model exists, run a drift check anyway
                try:
                    drift_report = compute_drift_report(session)
                    _store_drift_report(session, drift_report)
                    if drift_report.get("drift_detected"):
                        logger.warning(
                            "Drift detected during retrain skip: max_psi=%.4f on '%s'",
                            drift_report.get("max_psi", 0.0),
                            drift_report.get("max_psi_feature", ""),
                        )
                except Exception as drift_err:
                    logger.warning(
                        "Drift check during retrain skip failed (non-fatal): %s",
                        drift_err,
                    )
            return {"status": "ok" if trained else "skipped", "metrics": metrics}
        finally:
            session.close()
    except Exception as exc:
        logger.error("ML model retrain failed: %s", exc)
        try:
            raise self.retry(exc=exc, countdown=300)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


# Maintenance Tasks


@app.task(base=LoggedTask)
def cleanup_expired_otps_task() -> None:
    """Clean up expired OTP codes from the database."""
    try:
        from database.db_session import SessionLocal
        from database.models import OtpCode
        from utils.time import utc_now

        session = SessionLocal()
        try:
            result = (
                session.query(OtpCode)
                .filter(
                    OtpCode.expires_at < utc_now(),
                    OtpCode.is_used == False,
                )
                .delete()
            )
            session.commit()
            if result:
                logger.info("Cleaned up %d expired OTP codes", result)
            return {"status": "ok", "cleaned": result}
        finally:
            session.close()
    except Exception as exc:
        logger.error("OTP cleanup failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


@app.task(base=LoggedTask)
def cleanup_revoked_tokens_task() -> None:
    """Clean up expired revoked token entries."""
    try:
        from database.db_session import SessionLocal
        from database.models import RevokedToken
        from utils.time import utc_now

        session = SessionLocal()
        try:
            result = (
                session.query(RevokedToken)
                .filter(
                    RevokedToken.expires_at < utc_now(),
                )
                .delete()
            )
            session.commit()
            if result:
                logger.info("Cleaned up %d expired revoked tokens", result)
            return {"status": "ok", "cleaned": result}
        finally:
            session.close()
    except Exception as exc:
        logger.error("Token cleanup failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


# Export / Report Tasks


@app.task(base=LoggedTask, bind=True, max_retries=2)
def generate_export_task(
    self,
    export_type: str,
    filename: str,
    headers: list[str],
    rows: list[list[Any]],
    **kwargs,
):
    """Generate an export file as a background task.

    export_type: 'csv', 'xlsx', or 'pdf'
    """
    from services.export_service import ExportError, ExportService

    try:
        svc = ExportService()
        ext_map = {"csv": ".csv", "xlsx": ".xlsx", "pdf": ".pdf"}
        ext = ext_map.get(export_type, ".csv")
        full_name = filename if filename.endswith(ext) else f"{filename}{ext}"

        if export_type == "csv":
            result = svc.to_csv(full_name, headers, rows, **kwargs)
        elif export_type == "xlsx":
            result = svc.to_excel(full_name, headers, rows, **kwargs)
        elif export_type == "pdf":
            title = kwargs.pop("title", "Report")
            result = svc.to_pdf(full_name, title, headers, rows, **kwargs)
        else:
            raise ExportError(f"Unsupported export type: {export_type}")

        logger.info("Export generated: %s", result.path)
        return {"status": "ok", "path": result.path, "filename": result.filename}
    except Exception as exc:
        logger.error("Export generation failed: %s", exc)
        try:
            raise self.retry(exc=exc, countdown=60)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
