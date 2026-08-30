import os
import sys

# Set test secrets BEFORE any project imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only-not-for-production")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_session import Base
from services.analytics_service import AnalyticsService
from services.auth_service import AuthService
from services.student_service import StudentService


@pytest.fixture(scope="session")
def test_db() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def auth_service(test_db):
    return AuthService(test_db)


@pytest.fixture
def student_service(test_db):
    return StudentService(test_db)


@pytest.fixture
def analytics_service(test_db):
    return AnalyticsService(test_db)
