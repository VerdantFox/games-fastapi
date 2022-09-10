"""SQLModel models for working with both the database and FastAPI input/output."""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import NonNegativeInt, root_validator, validator
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel


# -----------------------------------------------------------------------------
# Games
# -----------------------------------------------------------------------------
def validate_max_players(cls: Any, fields: dict) -> dict:
    """max_players should always be >= min_players."""
    min_players = fields.get("min_players")
    max_players = fields.get("max_players")
    if max_players is None or min_players is None:
        return fields
    if max_players < min_players:
        raise ValueError("max_players must be >= min_players.")
    return fields


class GameBase(SQLModel):
    """Game base model that most other Games inherit from."""

    name: str = Field(index=True)
    description: Optional[str] = None
    company: Optional[str] = Field(default=None, index=True)
    release_year: Optional[int] = Field(default=None, index=True)
    genre: Optional[str] = Field(index=True)
    duration: NonNegativeInt = Field(index=True)
    min_age: Optional[NonNegativeInt] = Field(default=None, index=True)
    min_players: NonNegativeInt = Field(index=True)
    max_players: NonNegativeInt = Field(index=True)
    image: Optional[str] = None


class Game(GameBase, table=True):
    """Game table model. This is used for database operations.

    It will create the "game" table in the database, automatically.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    avg_rating: Optional[float] = Field(default=None, index=True)
    reviews: List["Review"] = Relationship(
        back_populates="game", sa_relationship_kwargs={"cascade": "delete"}
    )
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class GameCreate(GameBase):
    """Model for create input.

    Equivalent to GameBase, re-written for documentation purposes.
    """

    _max_players_validation = root_validator(allow_reuse=True)(validate_max_players)


class GameRead(GameBase):
    """Game model for read output, where the "id" field is ALWAYS included."""

    avg_rating: Optional[float] = None
    id: int
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class GameUpdate(SQLModel):
    """Game model for update input, all fields are optional."""

    name: Optional[str] = None
    description: Optional[str] = None
    company: Optional[str] = None
    release_year: Optional[int] = None
    genre: Optional[str] = None
    duration: Optional[NonNegativeInt] = None
    min_age: Optional[NonNegativeInt] = Field(default=None, index=True)
    min_players: Optional[NonNegativeInt] = None
    max_players: Optional[NonNegativeInt] = None
    image: Optional[str] = None

    _max_players_validation = root_validator(allow_reuse=True)(validate_max_players)


# -----------------------------------------------------------------------------
# Reviews
# -----------------------------------------------------------------------------
def validate_rating(cls: Any, value: int) -> int:
    """rating should always be between 1 and 5."""
    if not 1 <= value <= 5:
        raise ValueError("rating must be between 1 and 5")
    return value


class ReviewBase(SQLModel):
    """Review base model that most other Reviews inherit from."""

    game_id: int = Field(foreign_key="game.id")
    rating: int = Field(index=True)
    comment: Optional[str] = None


class Review(ReviewBase, table=True):
    """Review table model. This is used for database operations.

    It will create the "review" table in the database, automatically.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    game: Game = Relationship(back_populates="reviews")
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class ReviewCreate(ReviewBase):
    """Model for create input.

    Equivalent to ReviewBase, re-written for documentation purposes.
    """

    _rating_validation = validator("rating", allow_reuse=True)(validate_rating)


class ReviewRead(ReviewBase):
    """Review model for read output, where the "id" field is ALWAYS included."""

    id: int
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )


class ReviewUpdate(SQLModel):
    """Review model for read output, where the "id" field is ALWAYS included.

    Don't allow updating the game_id, as that would be a new review.
    """

    rating: Optional[int] = None
    comment: Optional[str] = None
    _rating_validation = validator("rating", allow_reuse=True)(validate_rating)


class GameReadWithReviews(GameRead):
    """Game model for read output including game reviews."""

    reviews: List[ReviewRead] = []


class ReviewReadWithGame(ReviewRead):
    """Review model for read output including game reviews."""

    game: GameRead


# -----------------------------------------------------------------------------
# General
# -----------------------------------------------------------------------------
class DeleteOk(SQLModel):
    """Model for delete output."""

    ok: bool = True
