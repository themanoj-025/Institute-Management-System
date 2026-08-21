import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import BASE_DIR, DATABASE_URL

# Ensure database directory exists
db_dir = os.path.join(BASE_DIR, "database")
os.makedirs(db_dir, exist_ok=True)

# Connection string & pooling
# Use PostgreSQL via ``DATABASE_URL`` env var, falling back to SQLite for
# local/offline desktop mode. PostgreSQL gets proper connection pooling.

_is_pg = DATABASE_URL.startswith("postgresql://")

if _is_pg:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,  # recycle connections after 1 hour
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


from collections.abc import Generator
from contextlib import contextmanager
from typing import Iterator


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_session() -> Iterator:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
