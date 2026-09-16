import os
from collections.abc import Iterator
from typing import Any

# Set test secrets BEFORE any project imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only-not-for-production")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base, init_db
from services.analytics_service import AnalyticsService
from services.auth_service import AuthService
from services.student_service import StudentService


@pytest.fixture(scope="session", autouse=True)
def _api_schema() -> Iterator[None]:
    """Bootstrap the app DB for API-level tests.

    Some test modules build ``TestClient`` at module import time, so the app's
    lifespan (and its schema bootstrap) never runs. Ensure ``init_app`` and
    ``init_db`` have run before any test touches the API.
    """
    from config.settings import init_app

    init_app()
    init_db()
    # Postgres enforces the revoked_tokens.user_id FK that SQLite ignores.
    # Blacklist tests reference user_id=1, so ensure that user exists.
    from config.settings import IS_POSTGRES

    if IS_POSTGRES:
        from database.db_session import SessionLocal
        from database.models import User, UserRole

        session = SessionLocal()
        try:
            if session.query(User).filter(User.id == 1).first() is None:
                session.add(
                    User(
                        id=1,
                        username="ci-test-user",
                        password_hash="test-hash-not-a-real-password",
                        role=UserRole.staff,
                    )
                )
                session.commit()
        finally:
            session.close()
    yield


@pytest.fixture(scope="session")
def test_db() -> Iterator[Any]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def auth_service(test_db) -> None:
    return AuthService(test_db)


@pytest.fixture
def student_service(test_db) -> None:
    return StudentService(test_db)


@pytest.fixture
def analytics_service(test_db) -> None:
    return AnalyticsService(test_db)
