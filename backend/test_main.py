import asyncio

import httpx
import pytest

import main
from main import COLUMNS, ROWS, app, game_board


@pytest.fixture(autouse=True)
def empty_board():
    """Keep tests isolated while preserving production's in-memory behavior."""

    for row in game_board:
        row[:] = [None] * COLUMNS
    main.current_player = main.FIRST_PLAYER
    yield


def api_request(method, path, **kwargs):
    """Send one in-process HTTP request without starting a server thread."""

    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_get_game_returns_empty_six_by_seven_board():
    response = api_request("GET", "/game")

    assert response.status_code == 200
    state = response.json()
    assert state["rows"] == ROWS
    assert state["columns"] == COLUMNS
    assert state["board"] == [[None] * COLUMNS for _ in range(ROWS)]
    assert state["full_columns"] == []
    assert state["current_player"] == "red"
    assert state["is_full"] is False
    assert state["winner"] is None


def test_moves_drop_to_lowest_row_and_persist():
    first_move = api_request("POST", "/game", json={"column": 2})
    assert first_move.status_code == 200
    assert first_move.json()["current_player"] == "yellow"

    refreshed_state = api_request("GET", "/game").json()
    assert refreshed_state["current_player"] == "yellow"

    second_move = api_request("POST", "/game", json={"column": 2})
    assert second_move.status_code == 200

    state = api_request("GET", "/game").json()
    assert state["board"][ROWS - 1][2] == "red"
    assert state["board"][ROWS - 2][2] == "yellow"
    assert state["board"][ROWS - 3][2] is None
    assert state["current_player"] == "red"


def test_full_column_is_disabled_and_rejected():
    for _ in range(ROWS):
        response = api_request("POST", "/game", json={"column": 4})
        assert response.status_code == 200

    assert response.json()["full_columns"] == [4]
    assert response.json()["is_full"] is False

    rejected = api_request("POST", "/game", json={"column": 4})
    assert rejected.status_code == 409
    assert rejected.json() == {"detail": "That column is full."}
    assert api_request("GET", "/game").json()["current_player"] == "red"


@pytest.mark.parametrize("column", [-1, COLUMNS])
def test_column_must_be_in_range(column):
    response = api_request("POST", "/game", json={"column": column})

    assert response.status_code == 422
    assert api_request("GET", "/game").json()["current_player"] == "red"


def test_client_cannot_choose_a_player_or_grid_cell():
    response = api_request(
        "POST", "/game", json={"column": 1, "row": 5, "player": "red"}
    )

    assert response.status_code == 422
    state = api_request("GET", "/game").json()
    assert state["board"] == [[None] * COLUMNS for _ in range(ROWS)]
    assert state["current_player"] == "red"


def test_full_board_is_reported_and_rejects_more_moves():
    draw_board = [
        ["red", "red", "yellow", "yellow", "red", "red", "yellow"],
        ["yellow", "yellow", "red", "red", "yellow", "yellow", "red"],
        ["red", "red", "yellow", "yellow", "red", "red", "yellow"],
        ["yellow", "yellow", "red", "red", "yellow", "yellow", "red"],
        ["red", "red", "yellow", "yellow", "red", "red", "yellow"],
        ["yellow", "yellow", "red", "red", "yellow", "yellow", "red"],
    ]
    for row_index, row in enumerate(draw_board):
        game_board[row_index][:] = row

    state = api_request("GET", "/game").json()
    assert state["is_full"] is True
    assert state["full_columns"] == list(range(COLUMNS))
    assert state["current_player"] == "red"
    assert state["winner"] is None

    rejected = api_request("POST", "/game", json={"column": 0})
    assert rejected.status_code == 409
    assert rejected.json() == {"detail": "The board is full."}
    assert api_request("GET", "/game").json()["current_player"] == "red"


def test_reset_clears_board_and_returns_turn_to_red():
    api_request("POST", "/game", json={"column": 0})
    api_request("POST", "/game", json={"column": 1})
    api_request("POST", "/game", json={"column": 2})

    response = api_request("DELETE", "/game")

    assert response.status_code == 200
    state = response.json()
    assert state["board"] == [[None] * COLUMNS for _ in range(ROWS)]
    assert state["full_columns"] == []
    assert state["current_player"] == "red"
    assert state["is_full"] is False
    assert state["winner"] is None


@pytest.mark.parametrize(
    "moves",
    [
        [0, 6, 1, 6, 2, 6, 3],  # horizontal
        [0, 1, 0, 1, 0, 1, 0],  # vertical
        [0, 1, 1, 2, 3, 2, 2, 3, 4, 3, 3],  # diagonal
        [6, 5, 5, 4, 3, 4, 4, 3, 2, 3, 3],  # opposite diagonal
    ],
)
def test_red_wins_in_every_direction(moves):
    for column in moves:
        response = api_request("POST", "/game", json={"column": column})
        assert response.status_code == 200

    state = response.json()
    assert state["winner"] == "red"
    assert state["current_player"] == "red"

    rejected = api_request("POST", "/game", json={"column": 5})
    assert rejected.status_code == 409
    assert rejected.json() == {"detail": "Red has won."}


def test_yellow_can_win_and_reset_still_works():
    for column in [0, 1, 0, 1, 2, 1, 2, 1]:
        response = api_request("POST", "/game", json={"column": column})
        assert response.status_code == 200

    assert response.json()["winner"] == "yellow"
    assert response.json()["current_player"] == "yellow"

    reset = api_request("DELETE", "/game")
    assert reset.status_code == 200
    assert reset.json()["winner"] is None
    assert reset.json()["current_player"] == "red"
