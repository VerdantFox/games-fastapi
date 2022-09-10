"""games: endpoints for /games."""
from typing import Optional

import pydantic
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from api.database import get_session

from .models import (
    DeleteOk,
    Game,
    GameCreate,
    GameRead,
    GameReadWithReviews,
    GameUpdate,
)

TAG_NAME = "Games"
TAG_DESCRIPTION = "Routes associated with games."
games_router = APIRouter(prefix="/games", tags=["Games"])


# -----------------------------------------------------------------------------
# Games endpoints
# -----------------------------------------------------------------------------
@games_router.post("", response_model=GameRead, status_code=201)
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
    limit: Optional[int] = Query(default=100, ge=1, le=100),
    name: Optional[str] = Query(None, min_length=1, alias="filter[name]"),
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
    return session.exec(query.offset(offset).limit(limit).order_by(Game.id)).all()


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
