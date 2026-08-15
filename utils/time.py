"""
Shared UTC datetime utilities.

Single source of truth for timestamp generation across the entire project.

Returns a **timezone-aware** UTC datetime (``tzinfo=timezone.utc``),
compatible with SQLAlchemy ``DateTime(timezone=True)`` columns
used across all models.

SQLite's local/offline mode stores aware datetimes as-is without
enforcement — SQLAlchemy's Python-side handling still round-trips
correctly because the datetime objects retain their ``tzinfo``.

Usage:
    from utils.time import utc_now
    now = utc_now()  # timezone-aware UTC datetime

    # Comparisons always work:
    assert now.tzinfo is not None
    assert utc_now() > now  # No TypeError
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    This is the canonical function for generating timestamps in the project.
    All models and services should import and use this instead of calling
    ``datetime.now()`` or ``datetime.utcnow()`` directly.

    The returned value is an **aware** UTC datetime with
    ``tzinfo=timezone.utc``, compatible with ``DateTime(timezone=True)``
    columns in PostgreSQL.  SQLite stores the value as-is — the Python
    ``tzinfo`` is preserved through SQLAlchemy's round-trip.

    Returns
    -------
    datetime
        Current UTC time with ``tzinfo=timezone.utc``.
    """
    return datetime.now(timezone.utc)
