# ADR-001: PostgreSQL as Production Database

**Status**: Accepted
**Date**: 2026-07-24 (updated 2026-07-25)
**Author**: Architecture Team

## Context

The original system used SQLite for all deployments (desktop and server). As we add a REST API with concurrent web/mobile clients, SQLite's single-writer model becomes a bottleneck. We need a database that supports concurrent writes (attendance marking, fee entry, result entry happening simultaneously) and provides production-grade reliability.

## Decision

Use **PostgreSQL 16** as the production database. Keep SQLite as the backend for the desktop/offline mode.

## Rationale

| Factor | PostgreSQL | SQLite |
| -------- | ----------- | -------- |
| **Concurrent writers** | Full MVCC; N concurrent writers | Single writer; serialized |
| **Connection pooling** | Native via PgBouncer / psycopg2 pool | `check_same_thread=False` (unsafe) |
| **Aggregate functions** | `SUM`, `COUNT`, `AVG` server-side | Same, but limited by single-writer |
| **Production ops** | Backups, replication, point-in-time recovery | File-level backup only |
| **JSON support** | Native JSONB | JSON functions (no binary) |
| **Full-text search** | `tsvector` / GIN indexes | FTS5 (optional module) |
| **Desktop/offline** | Requires network | Zero-config, single file |

## Timezone-Aware Datetime Handling (*Updated 2026-07-25*)

All model columns that represent timestamps now use `DateTime(timezone=True)`
in SQLAlchemy, which maps to `TIMESTAMP WITH TIME ZONE` (TIMESTAMPTZ) in
PostgreSQL. The shared utility `utc_now()` returns timezone-aware UTC
datetimes (`tzinfo=timezone.utc`).

A dedicated Alembic migration (`9a1b2c3d4e5f`) converts all 21 existing
`TIMESTAMP WITHOUT TIME ZONE` columns using:
```sql
ALTER TABLE <table> ALTER COLUMN <column> TYPE TIMESTAMPTZ
  USING <column> AT TIME ZONE 'UTC';
```

This correctly reinterprets existing naive values (which are already UTC)
as timezone-aware without shifting the actual time value.

**SQLite note**: SQLite has no native TIMESTAMPTZ type. SQLAlchemy handles
`DateTime(timezone=True)` at the Python/dialect level for SQLite. The `tzinfo`
is preserved through SQLAlchemy's round-trip but may not be enforced at the
storage layer. Code that compares stored datetimes against `utc_now()` in
SQLite should normalize to naive or aware consistently.

## Consequences

- **Migration script**: `scripts/migrate_sqlite_to_pg.py` copies data from existing SQLite to PostgreSQL
- **Connection string**: `DATABASE_URL` env var; defaults to SQLite for desktop
- **Alembic**: All migrations must be dialect-agnostic; use `batch_alter_table` for SQLite compatibility
- **Connection pooling**: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`
- **Timezone**: All timestamp columns are TIMESTAMPTZ; all code uses `utc_now()` as the single source of truth

## Related

- ADR-004: Timezone-Aware Datetimes
- `database/db_session.py` — Pooling configuration
- `scripts/migrate_sqlite_to_pg.py` — Migration script
- `utils/time.py` — `utc_now()` utility
