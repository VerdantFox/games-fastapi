"""conftest: root level pytest fixture module"""
from typing import Generator
from urllib.parse import quote_plus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.future import Engine
from sqlalchemy_utils.functions import create_database, database_exists, drop_database
from sqlmodel import Session, SQLModel

from api.app import app, register_blueprints
from api.database import get_engine, get_session
from api.environment import settings


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def register_blueprints_fixture() -> TestClient:
    """Register blueprints for the app"""
    register_blueprints(app)


@pytest.fixture(scope="session", autouse=True)
def postgres_create_teardown_db_fixture() -> Generator[
    None, None, None
]:  # pragma: no cover
    """Create the test postgres database for the test session and tear it down after."""
    if settings.in_mem_db:
        yield
        return
    POSTGRES_TEST_DB_URL = (
        "postgresql+psycopg2://"
        f"{quote_plus(settings.postgres_user)}:{quote_plus(settings.postgres_password)}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.test_db}"
    )
    create_database(POSTGRES_TEST_DB_URL)
    assert database_exists(POSTGRES_TEST_DB_URL)
    yield
    drop_database(POSTGRES_TEST_DB_URL)
    assert not database_exists(POSTGRES_TEST_DB_URL)


@pytest.fixture(autouse=True)
def postgres_setup_teardown_db_fixture(
    engine: Engine,
) -> Generator[None, None, None]:  # pragma: no cover
    """Setup and teardown the test postgres database for each test."""
    if settings.in_mem_db:
        yield
        return
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="engine")
def engine_fixture() -> Engine:
    """Get a new engine for each test."""
    settings.postgres_db = settings.test_db
    return get_engine()


@pytest.fixture(name="session")
def session_fixture(engine: Engine) -> Generator[Session, None, None]:
    """Fixture for creating a session for testing.

    Yields in with block to close session after test finishes."""

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """Creates a new test client for testing with a new session from the session fixture."""

    def get_session_override() -> Session:
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
