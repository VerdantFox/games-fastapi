"""test_reviews: tests for the /reviews endpoints."""
from typing import Any

from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session

from api.models import Game, Review, ReviewCreate
from tests.conftest import REVIEWS


@pytest.mark.parametrize("review", REVIEWS[:2])
def test_create_review_success(
    client: TestClient, session: Session, load_games: list[Game], review: dict
) -> None:
    """Test that creating reviews (/games/{game_id}/reviews POST) succeeds."""
    loaded_game = load_games[0]  # from GAME_MAX_FIELDS
    review["game_id"] = loaded_game.id
    response = client.post(
        "/reviews", json=review, headers={"Content-Type": "application/json"}
    )

    data = response.json()
    review_id = data.get("id")
    assert review_id is not None
    assert response.status_code == 201
    db_review = session.query(Review).filter(Review.id == review_id).first()
    assert db_review
    assert (
        ReviewCreate(**data)
        == ReviewCreate(**review)
        == ReviewCreate(**db_review.dict())
    )
    session.refresh(loaded_game)
    assert loaded_game.reviews
    assert loaded_game.avg_rating == db_review.rating


INVALID_REVIEWS = [
    pytest.param({"rating": 0}, id="rating < 1"),
    pytest.param({"rating": 6}, id="rating > 5"),
    pytest.param({"rating": "invalid"}, id="rating non-int"),
]


@pytest.mark.parametrize("review", INVALID_REVIEWS)
def test_create_review_invalid(
    client: TestClient, load_games: list[Game], review: dict
) -> None:
    """Test that creating reviews (/games/{game_id}/reviews POST) fails (422) with invalid data."""
    loaded_game = load_games[0]  # from GAME_MAX_FIELDS
    review["game_id"] = loaded_game.id
    response = client.post(
        "/reviews", json=review, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_create_review_game_not_found(client: TestClient) -> None:
    """Test that creating reviews (/reviews POST) fails (404) when game not found."""
    response = client.post(
        "/reviews",
        json={"game_id": 999, "rating": 5, "comment": "New Comment"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 404


REVIEWS_PARAMS = [
    # [offset, limit, game_id, expected_reviews]
    pytest.param(None, None, None, REVIEWS, id="no params"),
    pytest.param(None, 2, None, REVIEWS[:2], id="limit 2"),
    pytest.param(2, None, None, REVIEWS[2:], id="offset 2"),
    pytest.param(1, 2, None, REVIEWS[1:3], id="offset 1, limit 2"),
    pytest.param(None, None, 1, REVIEWS[:3], id="game_id 1"),
    pytest.param(1, 1, 1, [REVIEWS[1]], id="all params"),
    pytest.param(None, None, 999, [], id="game_id not found"),
]


@pytest.mark.parametrize(
    ("offset", "limit", "game_id", "expected_reviews"), REVIEWS_PARAMS
)
def test_get_reviews_success(
    client: TestClient,
    load_games_and_reviews: list[Game],
    offset: int,
    limit: int,
    game_id: int,
    expected_reviews: list[dict],
) -> None:
    """Test that getting reviews (/reviews GET) succeeds."""
    loaded_games, loaded_reviews = load_games_and_reviews
    params = {
        "offset": offset,
        "limit": limit,
        "filter[game_id]": game_id,
    }
    response = client.get("/reviews", params=params)
    data = response.json()
    actual = [ReviewCreate(**review) for review in data]
    expected = [ReviewCreate(**review) for review in expected_reviews]
    assert response.status_code == 200
    assert actual == expected


INVALID_REVIEW_PARAMS = [
    # [offset, limit, game_id]
    pytest.param("invalid", None, None, id="offset non-int"),
    pytest.param(None, "invalid", None, id="limit non-int"),
    pytest.param(None, None, "invalid", id="game_id non-int"),
    pytest.param(None, 101, None, id="limit > 100"),
    pytest.param(None, 0, None, id="limit < 1"),
    pytest.param(-1, None, None, id="offset < 0"),
]


@pytest.mark.parametrize(("offset", "limit", "game_id"), INVALID_REVIEW_PARAMS)
def test_get_reviews_invalid_params(
    client: TestClient, offset: Any, limit: Any, game_id: Any
) -> None:
    """Test that getting reviews (/reviews GET) fails (422) with invalid params."""
    params = {
        "offset": offset,
        "limit": limit,
        "filter[game_id]": game_id,
    }
    response = client.get("/reviews", params=params)
    assert response.status_code == 422


def test_get_review_success(
    client: TestClient, load_games_and_reviews: tuple[list[Game], list[Review]]
) -> None:
    """Test that getting a review (/reviews/{review_id} GET) succeeds."""
    loaded_games, _ = load_games_and_reviews
    game = loaded_games[0]
    review = game.reviews[0]
    response = client.get(f"/reviews/{review.id}")
    data = response.json()
    assert response.status_code == 200
    assert data["game"]["id"] == game.id
    assert ReviewCreate(**data) == ReviewCreate(**review.dict())


def test_get_review_not_found(client: TestClient) -> None:
    """Test that getting a review (/reviews/{review_id} GET) fails (404) when review not found."""
    response = client.get("/reviews/999")
    assert response.status_code == 404


VALID_UPDATES = [
    pytest.param({"rating": 3, "comment": "Updated Comment"}, id="all fields"),
    pytest.param({"rating": 3}, id="rating only"),
    pytest.param({"comment": "Updated Comment"}, id="comment only"),
    pytest.param({"comment": None}, id="comment null"),
]


@pytest.mark.parametrize("update", VALID_UPDATES)
def test_update_review_success(
    client: TestClient,
    load_games_and_reviews: tuple[list[Game], list[Review]],
    update: dict,
) -> None:
    """Test that updating a review (/reviews/{review_id} PATCH) succeeds."""
    loaded_games, _ = load_games_and_reviews
    game = loaded_games[0]
    review = game.reviews[0]
    response = client.patch(
        f"/reviews/{review.id}",
        json=update,
        headers={"Content-Type": "application/json"},
    )
    data = response.json()
    assert response.status_code == 200
    expected = review.dict() | update
    assert ReviewCreate(**data) == ReviewCreate(**expected)


INVALID_REVIEW_UPDATES = [
    pytest.param({"rating": 0}, id="rating < 1"),
    pytest.param({"rating": 6}, id="rating > 5"),
    pytest.param({"rating": "invalid"}, id="rating non-int"),
    pytest.param({"rating": None}, id="rating null"),
]


@pytest.mark.parametrize("update", INVALID_REVIEW_UPDATES)
def test_update_review_invalid_update(
    client: TestClient,
    load_games_and_reviews: tuple[list[Game], list[Review]],
    update: dict,
) -> None:
    """Test that updating a review (/reviews/{review_id} PATCH) fails (422) with invalid update."""
    loaded_games, _ = load_games_and_reviews
    game = loaded_games[0]
    review = game.reviews[0]
    response = client.patch(
        f"/reviews/{review.id}",
        json=update,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_update_review_not_found(client: TestClient) -> None:
    """Test that updating a review (/reviews/{review_id} PATCH) fails (404) when review not found."""
    response = client.patch(
        "/reviews/999",
        json={"rating": 3, "comment": "Updated Comment"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 404


def test_delete_review_success(
    client: TestClient,
    session: Session,
    load_games_and_reviews: tuple[list[Game], list[Review]],
) -> None:
    """Test that deleting a review (/reviews/{review_id} DELETE) succeeds."""
    loaded_games, _ = load_games_and_reviews
    game = loaded_games[0]
    review = game.reviews[0]
    review_id = review.id
    response = client.delete(f"/reviews/{review.id}")
    assert response.status_code == 200
    assert not session.query(Review).filter(Review.id == review_id).first()


def test_delete_review_not_found(client: TestClient) -> None:
    """Test that deleting a review (/reviews/{review_id} DELETE) fails (404) when review not found."""
    response = client.delete("/reviews/999")
    assert response.status_code == 404
