from sqlalchemy.exc import SQLAlchemyError

import json
import socket

from sqlalchemy.orm import Session

from database.models import ActivityLog
from utils.logger import setup_logger

# Single shared logger — replaces the previous dual-logger setup
logger = setup_logger("activity", context={"service": "activity", "version": "1.0"})


class ActivityService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.hostname = socket.gethostname()

    def log(
        self,
        user_id: int,
        action: str,
        module: str = "General",
        details: dict | None = None,
        result: str = "success",
    ) -> None:
        """Logs an activity for a given user to both Database and rotating files."""
        from utils.time import utc_now

        timestamp = utc_now()
        details_str = json.dumps(details) if details else ""

        # Log to file via the shared structured logger
        log_msg = f"UserID: {user_id} | Action: {action} | Module: {module} | Result: {result} | Details: {details_str}"
        extra = {"module": "activity", "user_id": user_id, "action": action}
        if result == "fail":
            logger.error(log_msg, extra={"extra_fields": {**extra, "result": "fail"}})
        else:
            logger.info(log_msg, extra={"extra_fields": extra})

        # Log to SQL DB
        try:
            entry = ActivityLog(
                user_id=user_id,
                action=f"{action} [{result}]",
                module=module,
                ip_address=self.hostname,
                timestamp=timestamp,
            )
            self.session.add(entry)
            self.session.commit()
        except (SQLAlchemyError, AttributeError) as e:
            self.session.rollback()
            logger.error(
                f"DB Logging failed: {str(e)}",
                extra={"extra_fields": {**extra, "db_error": str(e)}},
            )

    def get_logs(self, limit: int = 100) -> list[ActivityLog]:
        """Fetches the latest activity logs."""
        return (
            self.session.query(ActivityLog)
            .order_by(ActivityLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_user_logs(self, user_id: int, limit: int = 5) -> list[ActivityLog]:
        """Fetches the latest activity logs for a specific user."""
        return (
            self.session.query(ActivityLog)
            .filter(ActivityLog.user_id == user_id)
            .order_by(ActivityLog.timestamp.desc())
            .limit(limit)
            .all()
        )
