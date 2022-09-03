"""app: the FastAPI app with endpoints"""

from typing import Optional

import pydantic
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from api.database import create_db_and_tables, get_session
from api.environment import VERSION
from api.models import (
    DeleteOk,
    Game,
    GameCreate,
    GameRead,
    GameReadWithReviews,
    GameUpdate,
    Review,
    ReviewCreate,
    ReviewRead,
    ReviewReadWithGame,
    ReviewUpdate,
)

TITLE = "Games-FastAPI App"
DESCRIPTION = """An API for CRUD operations on games and game reviews.
Available at `/docs` or `/redoc`."""
TAGS = [
    {"name": "Games", "description": "Routes associated with games."},
    {"name": "Game reviews", "description": "Routes associated with game reviews."},
]


app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    openapi_tags=TAGS,
)

games_router = APIRouter(prefix="/games", tags=["Games"])
reviews_router = APIRouter(prefix="/reviews", tags=["Game reviews"])


def register_blueprints(app: FastAPI) -> None:
    """Add routes to the FastAPI app"""
    routes = [games_router, reviews_router]
    for route in routes:
        app.include_router(route)


@app.on_event("startup")
def on_startup() -> None:
    """Run these functions on app startup."""
    create_db_and_tables()
    register_blueprints(app)


# -----------------------------------------------------------------------------
# Games endpoints
# -----------------------------------------------------------------------------
@games_router.post("", response_model=GameRead)
def create_game(*, session: Session = Depends(get_session), game: GameCreate) -> Game:
    """Create a new game."""
    db_game = Game.from_orm(game)
    session.add(db_game)
    session.commit()
    session.refresh(db_game)
    return db_game


@games_router.get("", response_model=list[GameRead])
def read_games(
    *,
    session: Session = Depends(get_session),
    offset: Optional[int] = Query(default=0, ge=0),
    limit: Optional[int] = Query(default=100, gte=1, lte=100),
    name: Optional[str] = Query(None, min_length=1),
    avg_rating_ge: Optional[float] = Query(
        default=None, ge=0, le=5, alias="filter[avg_rating][ge]"
    ),
    avg_rating_le: Optional[float] = Query(
        default=None, ge=0, le=5, alias="filter[avg_rating][le]"
    ),
) -> list[Game]:
    """Read all games."""
    query = select(Game)
    if name is not None:
        query = query.where(Game.name == name)
    if avg_rating_ge is not None:
        query = query.where(col(Game.avg_rating) >= avg_rating_ge)
    if avg_rating_le is not None:
        query = query.where(col(Game.avg_rating) <= avg_rating_le)
    return session.exec(query.offset(offset).limit(limit)).all()


@games_router.get("/{game_id}", response_model=GameReadWithReviews)
def read_game(*, session: Session = Depends(get_session), game_id: int) -> Game:
    """Read a single game."""
    if game := session.get(Game, game_id):
        return game
    else:
        raise HTTPException(status_code=404, detail="Game not found")


@games_router.patch("/{game_id}", response_model=GameRead)
def update_game(
    *, session: Session = Depends(get_session), game_id: int, game: GameUpdate
) -> Game:
    """Update a game."""
    db_game = session.get(Game, game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    game_data = game.dict(exclude_unset=True)
    for key, value in game_data.items():
        setattr(db_game, key, value)
    try:
        # Validate the data before committing it to the database.
        GameCreate(**db_game.dict())
    except pydantic.error_wrappers.ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e
    session.add(db_game)
    session.commit()
    session.refresh(db_game)
    return db_game


@games_router.delete("/{game_id}", response_model=DeleteOk)
def delete_game(*, session: Session = Depends(get_session), game_id: int) -> DeleteOk:
    """Delete a game."""
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    session.delete(game)
    session.commit()
    return DeleteOk()


# -----------------------------------------------------------------------------
# Reviews endpoints
# -----------------------------------------------------------------------------
def update_game_avg_rating(game: Game, session: Session) -> None:
    """Update a game's average rating for update.

    Call when a rating is added, deleted, or updated."""
    if reviews := game.reviews:
        avg_rating = round(sum(review.rating for review in reviews) / len(reviews), 1)
    else:
        avg_rating = None
    game.avg_rating = avg_rating
    session.add(game)
    session.commit()


@reviews_router.post("", response_model=ReviewRead)
def create_review(
    *, session: Session = Depends(get_session), review: ReviewCreate
) -> Review:
    """Create a new review."""
    db_review = Review.from_orm(review)
    session.add(db_review)
    try:
        session.commit()
    except IntegrityError as e:
        msg = f"game.id {db_review.game_id} does not exist."
        raise HTTPException(status_code=404, detail=msg) from e
    session.refresh(db_review)
    game = db_review.game
    update_game_avg_rating(game=game, session=session)
    return db_review


@reviews_router.get("", response_model=list[ReviewRead])
def read_reviews(
    *,
    session: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, lte=100),
) -> list[Review]:
    """Read all reviews."""
    return session.exec(select(Review).offset(offset).limit(limit)).all()


@reviews_router.get("/{review_id}", response_model=ReviewReadWithGame)
def read_review(*, session: Session = Depends(get_session), review_id: int) -> Review:
    """Read a single review."""
    if review := session.get(Review, review_id):
        return review
    else:
        raise HTTPException(status_code=404, detail="Review not found")


@reviews_router.patch("/{review_id}", response_model=ReviewRead)
def update_review(
    *, session: Session = Depends(get_session), review_id: int, review: ReviewUpdate
) -> Review:
    """Update a review."""
    db_review = session.get(Review, review_id)
    if not db_review:
        raise HTTPException(status_code=404, detail="Review not found")
    review_data = review.dict(exclude_unset=True)
    for key, value in review_data.items():
        setattr(db_review, key, value)
    session.add(db_review)
    session.commit()
    session.refresh(db_review)
    game = db_review.game
    update_game_avg_rating(game=game, session=session)
    return db_review


@reviews_router.delete("/{review_id}", response_model=DeleteOk)
def delete_review(
    *, session: Session = Depends(get_session), review_id: int
) -> DeleteOk:
    """Delete a review."""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    game = review.game
    session.delete(review)
    session.commit()
    update_game_avg_rating(game=game, session=session)
    return DeleteOk()
