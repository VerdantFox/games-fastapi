"""app: the FastAPI app with endpoints."""
from fastapi import FastAPI

from api import games, reviews
from api.database import create_db_and_tables
from api.environment import VERSION

TITLE = "Games-FastAPI App"
DESCRIPTION = """An API for CRUD operations on games and game reviews.
Available at `/docs` or `/redoc`."""
TAGS = [
    {"name": module.TAG_NAME, "description": module.TAG_DESCRIPTION}
    for module in [games, reviews]
]


app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    openapi_tags=TAGS,
)


def register_blueprints(app: FastAPI) -> None:
    """Add routes to the FastAPI app."""
    routes = [games.games_router, reviews.reviews_router]
    for route in routes:
        app.include_router(route)


@app.on_event("startup")
def on_startup() -> None:  # pragma: no cover
    """Run these functions on app startup."""
    create_db_and_tables()
    register_blueprints(app)
