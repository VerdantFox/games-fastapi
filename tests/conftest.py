"""conftest: root level pytest fixture module"""
from typing import Generator
from urllib.parse import quote_plus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.future import Engine
from sqlalchemy_utils.functions import create_database, database_exists, drop_database
from sqlmodel import Session, SQLModel, select

from api.app import app, register_blueprints
from api.database import get_engine, get_session
from api.environment import settings
from api.models import Game, Review
from api.reviews import update_game_avg_rating


# -----------------------------------------------------------------------------
# General fixtures
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


# -----------------------------------------------------------------------------
# Shared endpoint fixtures
# -----------------------------------------------------------------------------
GAME_MAX_FIELDS = {
    "name": "Game all fields",
    "description": "Game 1 description.",
    "company": "Game 1 company",
    "release_year": 2000,
    "genre": "Game 1 genre",
    "duration": 15,
    "min_age": 10,
    "min_players": 1,
    "max_players": 100,
    "image": "./foo.png",
}
GAME_MIN_FIELDS = {
    "name": "Game min fields",
    "duration": 30,
    "min_age": 8,
    "min_players": 2,
    "max_players": 4,
}
GAMES = [
    GAME_MAX_FIELDS,
    GAME_MIN_FIELDS,
    {
        "name": "Game 3",
        "description": "Game 3 description.",
        "company": "Game 3 company",
        "release_year": 2000,
        "genre": "Game 3 genre",
        "duration": 45,
        "min_age": 12,
        "min_players": 3,
        "max_players": 6,
    },
]

# Assumes that above GAMES have ids 1, 2, 3
REVIEWS = [
    {"game_id": 1, "rating": 5},
    {"game_id": 1, "rating": 4, "comment": "Review 2 comment."},
    {"game_id": 1, "rating": 3, "comment": "Review 3 comment."},
    {"game_id": 2, "rating": 2, "comment": "Review 4 comment."},
    {"game_id": 2, "rating": 1, "comment": "Review 5 comment."},
]


@pytest.fixture(name="load_games")
def load_games_fixture(session: Session) -> list[Game]:
    """Load games into the database."""
    for game in GAMES:
        db_game = Game.parse_obj(game)
        session.add(db_game)
    session.commit()
    return session.exec(select(Game).order_by(Game.id)).all()


@pytest.fixture(name="load_games_and_reviews")
def load_games_and_reviews_fixture(
    session: Session, load_games: list[Game]
) -> tuple[list[Game], list[Review]]:
    """Load reviews into the database."""
    for review in REVIEWS:
        db_review = Review.parse_obj(review)
        session.add(db_review)
    session.commit()
    for game in load_games:
        update_game_avg_rating(game, session)
    reviews = session.exec(select(Review).order_by(Review.id)).all()
    games = session.exec(select(Game).order_by(Game.id)).all()
    return games, reviews
