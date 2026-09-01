"""
Celery task definitions for background/async work.

Tasks:
  - Email and notification sending
  - ML drift detection and model retraining
  - Scheduled cleanup (OTPs, revoked tokens)
  - Batch data exports
"""

from __future__ import annotations

import json
from typing import Any

from celery.exceptions import MaxRetriesExceededError

from celery_app import app, logger

# Email / Notification Tasks


@app.task(base=app.Task, bind=True, max_retries=3)
def send_email_task(
    self,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> dict[str, object]:
    """Send an email via SMTP as a background task."""
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
        msg.attach(MIMEText(html_body or body, "html" if html_body else "plain"))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
        server.quit()

        logger.info("Email sent to %s: %s", to_email, subject)
        return {"status": "sent", "to": to_email}
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        try:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


# Drift report storage helper


def _store_drift_report(session, report: dict) -> dict:
    """Write a drift report into SystemConfig."""
    from database.models import SystemConfig
    from utils.time import utc_now

    entries = [
        ("drift_detected", str(report.get("drift_detected", False)), "bool", "Whether ML feature drift has been detected"),
        ("drift_severe", str(report.get("severe_drift", False)), "bool", "Whether severe ML feature drift has been detected"),
        ("drift_max_psi", str(report.get("max_psi", 0.0)), "float", "Maximum PSI across all features"),
        ("drift_max_psi_feature", str(report.get("max_psi_feature", "")), "string", "Feature with highest PSI"),
        ("drift_features_drifted", str(report.get("features_drifted", 0)), "int", "Features exceeding PSI threshold"),
        ("drift_feature_count", str(report.get("feature_count", 0)), "int", "Total features compared"),
        ("drift_last_checked", utc_now().isoformat(), "string", "ISO timestamp of last drift check"),
        ("drift_error", str(report.get("error", "")), "string", "Error message from last drift check"),
    ]

    written = {}
    for key, value, value_type, description in entries:
        entry = session.query(SystemConfig).filter(SystemConfig.key == key).first()
        if entry:
            entry.value = value
            entry.value_type = value_type
        else:
            session.add(SystemConfig(key=key, value=value, value_type=value_type, description=description))
        written[key] = value
    session.commit()
    return written


# ML Tasks


@app.task(base=app.Task, bind=True, max_retries=1)
def check_ml_drift_task(self) -> None:
    """Run drift detection on current production features vs. reference."""
    try:
        from database.db_session import SessionLocal
        from ml.drift import compute_drift_report

        session = SessionLocal()
        try:
            report = compute_drift_report(session)
            _store_drift_report(session, report)
            if report.get("drift_detected"):
                logger.warning("ML drift detected! %d/%d features drifted.", report.get("features_drifted", 0), report.get("feature_count", 0))
            return {"status": "ok", "drift_detected": report.get("drift_detected")}
        finally:
            session.close()
    except (RuntimeError, ValueError, OSError) as exc:
        logger.error("ML drift check failed: %s", exc)
        try:
            raise self.retry(exc=exc, countdown=300)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


@app.task(base=app.Task, bind=True, max_retries=2)
def retrain_ml_model_task(self, force: bool = False) -> None:
    """Retrain the ML risk prediction model."""
    try:
        from database.db_session import SessionLocal
        from ml.service import MLService

        session = SessionLocal()
        try:
            svc = MLService()
            trained, metrics = svc.train(session, force=force)
            if trained:
                logger.info("ML model retrained: %s", json.dumps(metrics))
            return {"status": "ok" if trained else "skipped", "metrics": metrics}
        finally:
            session.close()
    except (RuntimeError, ValueError, OSError) as exc:
        logger.error("ML model retrain failed: %s", exc)
        try:
            raise self.retry(exc=exc, countdown=300)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}


# Maintenance Tasks


@app.task(base=app.Task)
def cleanup_expired_otps_task() -> None:
    """Clean up expired OTP codes from the database."""
    try:
        from database.db_session import SessionLocal
        from database.models import OtpCode
        from utils.time import utc_now

        session = SessionLocal()
        try:
            result = session.query(OtpCode).filter(OtpCode.expires_at < utc_now(), OtpCode.is_used == False).delete()
            session.commit()
            if result:
                logger.info("Cleaned up %d expired OTP codes", result)
            return {"status": "ok", "cleaned": result}
        finally:
            session.close()
    except Exception as exc:
        logger.error("OTP cleanup failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


@app.task(base=app.Task)
def cleanup_revoked_tokens_task() -> None:
    """Clean up expired revoked token entries."""
    try:
        from database.db_session import SessionLocal
        from database.models import RevokedToken
        from utils.time import utc_now

        session = SessionLocal()
        try:
            result = session.query(RevokedToken).filter(RevokedToken.expires_at < utc_now()).delete()
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


@app.task(base=app.Task, bind=True, max_retries=2)
def generate_export_task(self, export_type: str, filename: str, headers: list[str], rows: list[list[Any]], **kwargs) -> dict[str, object]:
    """Generate an export file as a background task."""
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
            result = svc.to_pdf(full_name, kwargs.pop("title", "Report"), headers, rows, **kwargs)
        else:
            raise ExportError(f"Unsupported export type: {export_type}")

        logger.info("Export generated: %s", result.path)
        return {"status": "ok", "path": result.path, "filename": result.filename}
    except (OSError, ValueError) as exc:
        logger.error("Export generation failed: %s", exc)
        try:
            raise self.retry(exc=exc, countdown=60)
        except MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
