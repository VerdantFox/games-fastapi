"""test_app: test routes/functions in api.app"""
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from api.app import update_game_avg_rating
from api.models import (
    Game,
    GameCreate,
    GameRead,
    GameReadWithReviews,
    Review,
    ReviewCreate,
)

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


# -----------------------------------------------------------------------------
# fixtures
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("game", GAMES)
def test_create_game_success(client: TestClient, session: Session, game: dict) -> None:
    """Test that creating a game (/games POST) succeeds with various fields."""
    response = client.post(
        "/games",
        json=game,
        headers={"Content-Type": "application/json"},
    )
    data = response.json()
    game_id = data.get("id")
    assert game_id is not None
    assert response.status_code == 201
    db_game = session.query(Game).filter(Game.id == game_id).first()
    assert db_game
    assert GameCreate(**data) == GameCreate(**game) == GameCreate(**db_game.dict())


INVALID_GAME_CREATES = [
    pytest.param({}, id="empty"),
    pytest.param({"name": "Ricochet Robots"}, id="missing fields"),
    pytest.param(
        GAME_MIN_FIELDS | {"release_year": "not_int"}, id="non-int release_year"
    ),
    pytest.param(GAME_MIN_FIELDS | {"duration": "not_int"}, id="non-int duration"),
    pytest.param(GAME_MIN_FIELDS | {"duration": -1}, id="duration < 0"),
    pytest.param(GAME_MIN_FIELDS | {"min_age": "not_int"}, id="non-int min_age"),
    pytest.param(GAME_MIN_FIELDS | {"min_age": -1}, id="min_age < 0"),
    pytest.param(
        GAME_MIN_FIELDS | {"min_players": "not_int"}, id="non-int min_players"
    ),
    pytest.param(GAME_MIN_FIELDS | {"min_players": -1}, id="min_players < 0"),
    pytest.param(
        GAME_MIN_FIELDS | {"max_players": "not_int"}, id="non-int max_players"
    ),
    pytest.param(
        GAME_MIN_FIELDS | {"min_players": 5, "max_players": 4}, id="min > max"
    ),
]


@pytest.mark.parametrize("game", INVALID_GAME_CREATES)
def test_create_game_invalid_fails(client: TestClient, game: dict) -> None:
    """Test that creating a game (/games POST) fails (422) with invalid body data."""
    response = client.post(
        "/games",
        json=game,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


GAMES_PARAMS = [
    # [offset, limit, name, avg_rating_ge, avg_rating_le, expected_games]
    [None, None, None, None, None, GAMES],
    [0, 10, None, None, None, GAMES],
    [0, 2, None, None, None, GAMES[:2]],
    [2, 1, None, None, None, [GAMES[2]]],
    [None, None, "Game 3", None, None, [GAMES[2]]],
    [None, None, "Game", None, None, []],
    [None, None, None, 3, None, [GAMES[0]]],
    [None, None, None, None, 3, [GAMES[1]]],
]


@pytest.mark.parametrize(
    "offset, limit, name, avg_rating_ge, avg_rating_le, expected_games", GAMES_PARAMS
)
def test_read_games_succeeds(
    client: TestClient,
    load_games_and_reviews: list[Game],
    offset: int,
    limit: int,
    name: str,
    avg_rating_ge: int,
    avg_rating_le: int,
    expected_games: list[dict],
) -> None:
    """Test that reading games (/games GET) succeeds."""
    loaded_games, loaded_reviews = load_games_and_reviews
    params = {
        "offset": offset,
        "limit": limit,
        "filter[name]": name,
        "filter[avg_rating][ge]": avg_rating_ge,
        "filter[avg_rating][le]": avg_rating_le,
    }
    response = client.get("/games", params=params)
    data = response.json()
    actual = [GameCreate(**game) for game in data]
    expected = [GameCreate(**game) for game in expected_games]
    assert response.status_code == 200
    assert actual == expected


def test_read_game_succeeds(
    client: TestClient, load_games_and_reviews: tuple[list[Game], list[Review]]
) -> None:
    """Test that reading individual games (/games/{game_id} GET) succeeds."""
    loaded_games, _ = load_games_and_reviews
    for game in loaded_games:
        response = client.get(f"/games/{game.id}")
        assert response.status_code == 200
        data = response.json()
        assert GameReadWithReviews(**data) == GameReadWithReviews.from_orm(game)


def test_read_game_not_found(client: TestClient) -> None:
    """Test that reading individual games (/games/{game_id} GET) fails (404) when game not found."""
    response = client.get("/games/999")
    assert response.status_code == 404


VALID_UPDATES = [
    pytest.param({"name": "New Name"}, id="name"),
    pytest.param({"description": "new description"}, id="description"),
    pytest.param({"release_year": 2021, "genre": "new genre"}, id="release_year+genre"),
    pytest.param({"duration": 200, "min_age": 40}, id="duration+min_age"),
    pytest.param({"min_players": 5, "max_players": 10}, id="min_players+max_players"),
    pytest.param({"image": "./new_image.jpg"}, id="img"),
    pytest.param(
        {
            "description": None,
            "company": None,
            "release_year": None,
            "genre": None,
            "min_age": None,
        },
        id="All optionals to null",
    ),
]


@pytest.mark.parametrize("update", VALID_UPDATES)
def test_update_game_success(
    client: TestClient, load_games: list[Game], update: dict
) -> None:
    """Test that updating individual games (/games/{game_id} PATCH) succeeds."""
    loaded_game = load_games[0]  # from GAME_MAX_FIELDS
    response = client.patch(
        f"/games/{loaded_game.id}",
        json=update,
        headers={"Content-Type": "application/json"},
    )
    data = response.json()
    assert response.status_code == 200
    updated_game = GameRead.from_orm(loaded_game)
    assert GameRead(**data) == updated_game
    for key, value in update.items():
        assert getattr(updated_game, key) == value


INVALID_UPDATES = [
    pytest.param({"name": None}, id="null name"),
    pytest.param({"duration": None}, id="null duration"),
    pytest.param({"min_players": None}, id="null min_players"),
    pytest.param({"max_players": None}, id="null max_players"),
    pytest.param({"release_year": "non-int"}, id="non-int release_year"),
    pytest.param({"duration": "non-int"}, id="non-int duration"),
    pytest.param({"min_age": "non-int"}, id="non-int min_age"),
    pytest.param({"min_players": "non-int"}, id="non-int min_players"),
    pytest.param({"max_players": "non-int"}, id="non-int max_players"),
    pytest.param({"duration": -1}, id="duration < 0"),
    pytest.param({"min_age": -1}, id="min_age < 0"),
    pytest.param({"min_players": -1}, id="min_players < 0"),
    pytest.param({"min_players": 4, "max_players": 2}, id="max_players < min_players"),
]


@pytest.mark.parametrize("update", INVALID_UPDATES)
def test_update_game_invalid(
    client: TestClient, load_games: list[Game], update: dict
) -> None:
    """Test that updating individual games (/games/{game_id} PATCH) fails (422) with invalid data."""
    loaded_game = load_games[0]  # from GAME_MAX_FIELDS
    response = client.patch(
        f"/games/{loaded_game.id}",
        json=update,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_update_game_not_found(client: TestClient) -> None:
    """Test that updating individual games (/games/{game_id} PATCH) fails (404) when game not found."""
    response = client.patch(
        "/games/999",
        json={"name": "New Name"},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 404


def test_delete_succeeds(
    client: TestClient,
    session: Session,
    load_games_and_reviews: tuple[list[Game], list[Review]],
) -> None:
    """Test that deleting games (/games/{game_id} DELETE) succeeds.

    Also tests that deleting a game also deletes its reviews."""
    loaded_games, loaded_reviews = load_games_and_reviews
    loaded_game = loaded_games[0]  # from GAME_MAX_FIELDS
    game_id = loaded_game.id
    assert loaded_game.reviews
    response = client.delete(f"/games/{game_id}")
    assert response.status_code == 200
    assert not session.query(Game).filter(Game.id == game_id).first()
    assert not session.query(Review).filter(Review.game_id == game_id).first()


def test_delete_not_found(client: TestClient) -> None:
    """Test that deleting games (/games/{game_id} DELETE) fails (404) when game not found."""
    response = client.delete("/games/999")
    assert response.status_code == 404


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


@pytest.mark.parametrize("offset, limit, game_id, expected_reviews", REVIEWS_PARAMS)
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


@pytest.mark.parametrize("offset, limit, game_id", INVALID_REVIEW_PARAMS)
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
