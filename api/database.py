"""store: code for interacting with the postgres database"""
from typing import Generator
from urllib.parse import quote_plus

from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from api.environment import settings

if settings.in_mem_db:
    engine = create_engine(
        "sqlite://",  # Tells SQLModel we want to use an in-memory SQLite database.
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Use same in-memory db on different threads
    )
else:
    POSTGRES_DB_URL = (
        "postgresql+psycopg2://"
        f"{quote_plus(settings.postgres_user)}:{quote_plus(settings.postgres_password)}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    engine = create_engine(POSTGRES_DB_URL, echo=settings.echo_db)


def create_db_and_tables() -> None:
    """Create the database and tables from the SQLModel models.

    Note we must import the models first for this to work,
    even if we don't use them in this module.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a session in a context block for FastAPI dependency injection."""
    with Session(engine) as session:
        yield session
