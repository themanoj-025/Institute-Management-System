"""
Shared logging configuration for the BB-IMS application.

Features:
  - Structured JSON log file (logs/bb-ims.jsonl) rotated at 5 MB, 3 backups
  - Human-readable console output with colours
  - Extra context fields via ``extra`` dict passed to log calls

Usage:
  from utils.logger import setup_logger
  log = setup_logger("my-module")
  log.info("Hello", extra={"user_id": 42, "module": "auth"})
  log.error("Something broke")
"""

import json
import logging
import os
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "bb-ims.jsonl"  # JSON Lines format for structured logging
MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
BACKUP_COUNT = 3  # keep up to 3 rotated files

# Cached loggers so repeated calls to setup_logger return the same instance
_configured_loggers: set[str] = set()


class JSONFormatter(logging.Formatter):
    """Format log records as newline-delimited JSON for structured ingestion.

    Every log line is a valid JSON object with ``timestamp``, ``level``,
    ``logger``, ``message``, and any extra context keys passed via
    ``extra={...}`` in the log call.
    """

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[0]:
            base["exception"] = {
                "type": record.exc_info[0].__name__,
                "value": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        # Merge any extra context fields passed by the caller
        extra = getattr(record, "extra_fields", None)
        if extra:
            base.update(extra)

        return json.dumps(base, default=str, ensure_ascii=False)


class ContextLogger(logging.LoggerAdapter):
    """A logger adapter that merges a fixed set of context keys into every
    log call's ``extra`` dict.

    Usage::

        log = ContextLogger(logger, {"service": "api", "version": "1.0"})
        log.info("Request started")   # JSON line includes service+version
    """

    def process(self, msg: str, kwargs: Any) -> tuple:
        extra: dict[str, Any] = kwargs.get("extra", {})
        extra.setdefault("extra_fields", {})
        extra["extra_fields"].update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def _ensure_log_dir() -> None:
    """Create the logs directory if it doesn't exist."""
    os.makedirs(LOG_DIR, exist_ok=True)


def _file_formatter() -> logging.Formatter:
    return JSONFormatter()


def _console_formatter() -> logging.Formatter:
    """Compact human-readable formatter for the console."""
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def setup_logger(
    name: str,
    level: int = logging.DEBUG,
    context: dict[str, Any] | None = None,
) -> logging.Logger | ContextLogger:
    """
    Get or create a logger with both JSON file and console handlers.

    Parameters
    ----------
    name : str
        Logger name (hierarchical dotted name, e.g. ``"api.auth"``).
    level : int
        Logging level for both handlers (default ``logging.DEBUG``).
    context : dict, optional
        Static key-value pairs injected into every JSON log line for this
        logger (e.g. ``{"service": "api", "version": "1.0"}``).

    Returns
    -------
    logging.Logger
        A configured ``Logger`` instance. If *context* was provided, returns
        a ``ContextLogger`` adapter instead.
    """
    logger = logging.getLogger(name)

    if name in _configured_loggers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    _ensure_log_dir()

    # --- File handler (rotating, JSON format) ---
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(_file_formatter())
    logger.addHandler(file_handler)

    # --- Console handler (human-readable) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(_console_formatter())
    logger.addHandler(console_handler)

    _configured_loggers.add(name)

    # Bootstrap message
    logger.debug(
        "Logger initialised",
        extra={
            "extra_fields": {
                "log_file": str(LOG_FILE),
                "log_level": logging.getLevelName(level),
            }
        },
    )

    if context:
        return ContextLogger(logger, context)

    return logger


def shutdown() -> None:
    """Flush and close all logging handlers (call on app exit)."""
    logging.shutdown()
