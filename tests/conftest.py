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


@pytest.fixture(autouse=True)
def _isolated_ml_model_dir(tmp_path_factory, monkeypatch):
    """Redirect ML model writes to a temp dir.

    The risk model is lazily trained on first use, so any test touching
    ``MLService`` can rewrite the tracked ``ml/models/`` files (fresh
    ``saved_at`` timestamp in ``risk_v1_meta.json``, regenerated
    ``reference_distributions.json``), churning the working tree on every
    test run. Reads still work: existing tracked files are copied into the
    sandbox first.
    """
    import shutil

    from ml.drift_psi import MODELS_DIR as real_models_dir

    models_dir = tmp_path_factory.mktemp("ml_models")
    # Copy every tracked ML model artifact (not just the canonical three) so
    # that ML training/eval tests can rewrite them without touching the
    # committed files in the working tree.
    for src in sorted(real_models_dir.iterdir()):
        if src.is_file() and src.name.endswith(".json"):
            shutil.copy(src, models_dir / src.name)
    monkeypatch.setattr("ml.registry.MODELS_DIR", models_dir)
    reference_file = models_dir / "reference_distributions.json"
    monkeypatch.setattr("ml.drift.REFERENCE_FILE", reference_file)
    monkeypatch.setattr("ml.drift_psi.REFERENCE_FILE", reference_file)
    # Also redirect the drift sub-module's reference file if it posts its own
    # writes somewhere else.
    import ml.drift as drift_module
    if hasattr(drift_module, "MODELS_DIR"):
        monkeypatch.setattr("ml.drift.MODELS_DIR", models_dir)


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
