"""
Application configuration — single source of truth for all settings.

Reads from environment variables (via python-dotenv), with sensible
production defaults. No secrets are hardcoded or stored in config files.

Usage:
    from config.settings import (
        DATABASE_URL, SECRET_KEY, REDIS_URL, ...
    )

    # After import, call init_app() once during app bootstrap:
    from config.settings import init_app
    init_app()
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Paths (no side effects at import time)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Environment
ENV = os.getenv("ENV", "development")
IS_DEV = ENV == "development"

# Database
DB_PATH = os.getenv("DB_PATH", "database/bb_ims.db")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, DB_PATH)}",
)
IS_POSTGRES = DATABASE_URL.startswith("postgresql://")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Security
SECRET_KEY = os.environ["SECRET_KEY"]  # Required — app fails to start if missing
BCRYPT_COST = int(os.getenv("BCRYPT_COST", "14"))
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME_MINUTES = 15
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Email
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_ENABLED = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

# File Uploads
UPLOAD_DIR = os.path.join(BASE_DIR, "database", "uploads")
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx"}
MAX_UPLOAD_SIZE_MB = 5

# App Bootstrap

_initialized = False


def init_app():
    """Create necessary directories on app startup.

    Call this once during application bootstrap, never at import time.
    This replaces the previous module-level ``os.makedirs()`` calls
    that ran on every import.
    """
    global _initialized
    if _initialized:
        return
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "assets", "profiles"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "exports", "generated"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
    _initialized = True
