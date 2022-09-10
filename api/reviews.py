"""reviews: endpoints for reviews."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from api.database import get_session

from .models import (
    DeleteOk,
    Game,
    Review,
    ReviewCreate,
    ReviewRead,
    ReviewReadWithGame,
    ReviewUpdate,
)

TAG_NAME = "Game reviews"
TAG_DESCRIPTION = "Routes associated with game reviews."
reviews_router = APIRouter(prefix="/reviews", tags=["Game reviews"])


# -----------------------------------------------------------------------------
# Helper functions
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


# -----------------------------------------------------------------------------
# Reviews endpoints
# -----------------------------------------------------------------------------
@reviews_router.post("", response_model=ReviewRead, status_code=201)
def create_review(
    *, session: Session = Depends(get_session), review: ReviewCreate
) -> Review:
    """Create a new review."""
    db_review = Review.from_orm(review)
    if not (game := session.get(Game, review.game_id)):
        raise HTTPException(status_code=404, detail="Game not found")
    session.add(db_review)
    session.commit()
    update_game_avg_rating(game=game, session=session)
    return db_review


@reviews_router.get("", response_model=list[ReviewRead])
def read_reviews(
    *,
    session: Session = Depends(get_session),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    game_id: int = Query(None, ge=1, alias="filter[game_id]"),
) -> list[Review]:
    """Read all reviews."""
    query = select(Review)
    if game_id:
        query = query.where(Review.game_id == game_id)
    return session.exec(query.offset(offset).limit(limit).order_by(Review.id)).all()


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
