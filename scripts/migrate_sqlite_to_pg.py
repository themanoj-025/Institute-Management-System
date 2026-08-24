#!/usr/bin/env python3
"""
One-time data migration: SQLite → PostgreSQL.

Copies all tables from an existing SQLite database into a PostgreSQL
database, preserving IDs, relationships, and sequence state.

Usage:
    python scripts/migrate_sqlite_to_pg.py \\
        --sqlite path/to/bb_ims.db \\
        --pg-url postgresql://user:pass@host:5432/bb_ims

Requirements:
    pip install psycopg2-binary sqlalchemy

Caution:
    This script DROPS all existing data in the PostgreSQL target before
    copying. Run on a fresh/empty PostgreSQL database.
"""

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import Session


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite database to PostgreSQL")
    parser.add_argument(
        "--sqlite",
        required=True,
        help="Path to the SQLite database file (e.g., database/bb_ims.db)",
    )
    parser.add_argument(
        "--pg-url",
        required=True,
        help="PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/bb_ims)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without executing",
    )
    args = parser.parse_args()

    print(f"🔍 Connecting to SQLite: {args.sqlite}")
    sqlite_engine = create_engine(f"sqlite:///{args.sqlite}")
    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    print(f"🔍 Connecting to PostgreSQL: {args.pg_url}")
    pg_engine = create_engine(args.pg_url)

    # Reflect PostgreSQL schema (must already exist)
    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)

    # Determine which tables exist in both databases
    sqlite_tables = set(sqlite_meta.tables.keys())
    pg_tables = set(pg_meta.tables.keys())

    common_tables = sqlite_tables & pg_tables
    missing_in_pg = sqlite_tables - pg_tables

    print(f"\n📊 Tables found in SQLite: {len(sqlite_tables)}")
    print(f"📊 Tables found in PostgreSQL: {len(pg_tables)}")
    print(f"🔄 Tables to migrate: {len(common_tables)}")
    if missing_in_pg:
        print(f"⚠️  Tables in SQLite but NOT in PostgreSQL (skipped): {missing_in_pg}")

    if not common_tables:
        print("❌ No common tables to migrate. Ensure Alembic has been run on PostgreSQL first.")
        sys.exit(1)

    # Order tables by dependency (parents first, children last)
    # Hard-code a reasonable order based on the schema
    ordered_tables = [
        "users",
        "courses",
        "course_modules",
        "sessions",
        "staff",
        "subjects",
        "students",
        "attendances",
        "staff_attendances",
        "results",
        "leaves",
        "feedbacks",
        "fees",
        "fee_payments",
        "notices",
        "timetables",
        "activity_logs",
        "enquiries",
        "placements",
        "system_config",
        "otp_codes",
        "revoked_tokens",
    ]

    # Filter to only common tables, preserving order
    ordered_common = [t for t in ordered_tables if t in common_tables]

    with Session(pg_engine) as pg_session:
        if not args.dry_run:
            # Disable FK checks for bulk insert
            pg_session.execute(text("SET session_replication_role = 'replica';"))

        total_rows = 0
        for table_name in ordered_common:
            sqlite_table = sqlite_meta.tables[table_name]
            pg_table = pg_meta.tables[table_name]

            # Read from SQLite
            with sqlite_engine.connect() as sqlite_conn:
                rows = sqlite_conn.execute(sqlite_table.select()).fetchall()

            print(f"\n📋 {table_name}: {len(rows)} rows")

            if not rows:
                continue

            # Convert row data (handle type differences)
            converted_rows = []
            columns = [col.name for col in pg_table.columns]

            for row in rows:
                row_dict = dict(row._mapping)
                converted = {}
                for col_name in columns:
                    if col_name not in row_dict:
                        continue
                    val = row_dict[col_name]

                    # Handle type conversions
                    if isinstance(val, Decimal):
                        val = float(val)
                    elif isinstance(val, bytes) and table_name == "alembic_version":
                        val = val.decode("utf-8")
                    elif isinstance(val, datetime) and val.tzinfo is None:
                        # SQLite returns naive; PostgreSQL needs timezone-aware
                        val = val  # Will be treated as UTC by default
                    elif isinstance(val, date) and not isinstance(val, datetime):
                        val = val
                    elif isinstance(val, bool):
                        val = bool(val)

                    converted[col_name] = val

                converted_rows.append(converted)

            if not args.dry_run:
                # Batch insert in chunks
                chunk_size = 500
                for i in range(0, len(converted_rows), chunk_size):
                    chunk = converted_rows[i : i + chunk_size]
                    pg_session.execute(pg_table.insert(), chunk)
                pg_session.commit()
                print(f"  ✅ Copied {len(converted_rows)} rows to PostgreSQL")

            total_rows += len(converted_rows)

        if not args.dry_run:
            # Re-enable FK checks
            pg_session.execute(text("SET session_replication_role = 'origin';"))
            pg_session.commit()

            # Reset sequences for auto-increment IDs
            print("\n🔄 Resetting sequences...")
            _VALID_TABLES = set(ordered_tables)
            for table_name in ordered_common:
                pg_table = pg_meta.tables.get(table_name)
                if pg_table is None:
                    continue
                # Check if there's an 'id' column with autoincrement
                id_col = pg_table.columns.get("id")
                if id_col is not None and id_col.autoincrement:
                    # Validate table name against whitelist before interpolation
                    assert table_name in _VALID_TABLES, f"Unknown table: {table_name}"
                    max_id = pg_session.execute(
                        text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
                    ).scalar()
                    seq_name = f"{table_name}_id_seq"
                    pg_session.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH {max_id + 1}"))
            pg_session.commit()

    print(f"\n{'=' * 60}")
    print(f"✅ Migration complete! {total_rows} total rows copied.")
    print(f"{'=' * 60}")
    print("\n📌 Next steps:")
    print(f"   1. Run the app with DATABASE_URL={args.pg_url}")
    print("   2. Verify data integrity with spot checks")
    print("   3. Update your .env file to point DATABASE_URL to PostgreSQL")
    print("   4. Delete or archive the old SQLite database")


if __name__ == "__main__":
    main()
