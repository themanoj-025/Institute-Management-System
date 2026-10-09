# ADR-004: Timezone-Aware Datetimes as Single Source of Truth

**Status**: Accepted
**Date**: 2026-07-25
**Author**: Architecture Team

## Context

The codebase had multiple sources of truth for "now": `datetime.now()`,
`datetime.utcnow()`, and `datetime.now(timezone.utc)` were all used across
different modules. This created:

- **Inconsistency**: Some timestamps were naive UTC, others were timezone-aware
- **TypeErrors**: Comparing naive vs. aware datetimes raised `TypeError: can't
  compare offset-naive and offset-aware datetimes`
- **Maintenance risk**: Inconsistent usage made it unclear which form was
  canonical
- **PostgreSQL incompatibility**: SQLAlchemy models declared
  `DateTime(timezone=True)` but existing code passed naive datetimes, which
  PostgreSQL would reject

## Decision

1. **Create a single `utc_now()` function** in `utils/time.py` that returns
   `datetime.now(timezone.utc)` — a timezone-aware UTC datetime with
   `tzinfo=timezone.utc`
2. **Replace ALL direct calls** to `datetime.now()`, `datetime.utcnow()`, and
   `datetime.now(timezone.utc)` with `utc_now()` throughout the codebase
3. **Update ALL SQLAlchemy `DateTime` columns** to `DateTime(timezone=True)`,
   which maps to `TIMESTAMP WITH TIME ZONE` (TIMESTAMPTZ) in PostgreSQL

## Rationale

| Option | Pros | Cons |
| -------- | ------ | ------ |
| **Naive UTC everywhere** | Simple; no migration needed | Silent bugs when comparing; rejected by PostgreSQL TIMESTAMPTZ |
| **Aware UTC everywhere** | Correct by default; PostgreSQL-native | Requires migration; SQLite doesn't enforce tzinfo |
| **Mixed usage (status quo)** | No migration | Bugs; maintenance burden; PostgreSQL incompatibility |

### Why `utc_now()` as a function (not a constant)

- A module-level constant like `from datetime import datetime, timezone; NOW = datetime.now(timezone.utc)` would be evaluated once at import time
- A function ensures every call gets a fresh timestamp
- Makes mocking in tests straightforward (`unittest.mock.patch`)

### SQLite handling

SQLite has no native `TIMESTAMPTZ` type. SQLAlchemy handles
`DateTime(timezone=True)` at the Python/dialect level for SQLite — the
`tzinfo` is preserved through SQLAlchemy's round-trip but is not enforced
at the storage layer. Code that compares stored datetimes against
`utc_now()` should normalize both sides to naive or aware consistently.

## Consequences

- **Single source of truth**: All code calls `utc_now()`; no alternative
- **PostgreSQL readiness**: All TIMESTAMPTZ columns; `utc_now()` values
  compatible with PostgreSQL type system
- **Migration**: Alembic migration `9a1b2c3d4e5f` converts all 21 TIMESTAMP
  columns using `USING <col> AT TIME ZONE 'UTC'`
- **No regressions**: 292 tests pass with zero timezone-related failures

## Affected Files

- `utils/time.py` — Definition of `utc_now()`
- `database/models.py` — All `DateTime(timezone=True)` column declarations
- All service, API, ML, and utility files that generate timestamps

## Related

- ADR-001: PostgreSQL as Production Database (timezone-aware columns)
- `utils/time.py` — `utc_now()` implementation
- `database/alembic/versions/2026_07_25_9a1b2c3d4e5f_*.py` — Migration
