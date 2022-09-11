"""test_games: tests for the /games endpoints."""
from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session

from api.models import Game, GameCreate, GameRead, GameReadWithReviews, Review
from tests.conftest import GAME_MIN_FIELDS, GAMES


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
    ("offset", "limit", "name", "avg_rating_ge", "avg_rating_le", "expected_games"),
    GAMES_PARAMS,
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
