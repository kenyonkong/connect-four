"""FastAPI application for the Connect Four starter project."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


ROWS = 6
COLUMNS = 7
FIRST_PLAYER = "red"
SECOND_PLAYER = "yellow"
WIN_LENGTH = 4


def create_empty_board() -> list[list[str | None]]:
    """Create a new top-to-bottom Connect Four board."""

    return [[None for _ in range(COLUMNS)] for _ in range(ROWS)]


# This state lives for the lifetime of this Python process only.
game_board = create_empty_board()
current_player = FIRST_PLAYER


class HealthResponse(BaseModel):
    """Response returned by the health check endpoint."""

    status: str
    service: str


class MoveRequest(BaseModel):
    """A request to drop a piece into a zero-based column."""

    model_config = ConfigDict(extra="forbid")

    column: int = Field(ge=0, lt=COLUMNS)


class GameState(BaseModel):
    """The complete state needed to render the game."""

    rows: int
    columns: int
    board: list[list[str | None]]
    full_columns: list[int]
    current_player: str
    is_full: bool
    winner: str | None


app = FastAPI(
    title="Full-stack Starter API",
    description="Backend API for the React and Vite frontend.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """Report whether the API is available."""

    return HealthResponse(status="ok", service="backend")


def current_game_state() -> GameState:
    """Return a snapshot of the current in-memory board."""

    full_columns = [
        column for column in range(COLUMNS) if game_board[0][column] is not None
    ]

    return GameState(
        rows=ROWS,
        columns=COLUMNS,
        board=[row.copy() for row in game_board],
        full_columns=full_columns,
        current_player=current_player,
        is_full=len(full_columns) == COLUMNS,
        winner=find_winner(),
    )


def find_winner() -> str | None:
    """Return the color with four connected pieces, if one exists."""

    directions = (
        (0, 1),  # horizontal
        (1, 0),  # vertical
        (1, 1),  # diagonal down-right
        (1, -1),  # diagonal down-left
    )

    for row in range(ROWS):
        for column in range(COLUMNS):
            player = game_board[row][column]
            if player is None:
                continue

            for row_step, column_step in directions:
                end_row = row + (WIN_LENGTH - 1) * row_step
                end_column = column + (WIN_LENGTH - 1) * column_step
                if not (0 <= end_row < ROWS and 0 <= end_column < COLUMNS):
                    continue

                if all(
                    game_board[row + offset * row_step][
                        column + offset * column_step
                    ]
                    == player
                    for offset in range(1, WIN_LENGTH)
                ):
                    return player

    return None


@app.get("/game", response_model=GameState, tags=["game"])
async def get_game() -> GameState:
    """Return the current game state."""

    return current_game_state()


@app.post("/game", response_model=GameState, tags=["game"])
async def make_move(move: MoveRequest) -> GameState:
    """Drop one piece into the lowest available row in a column."""

    global current_player

    if winner := find_winner():
        raise HTTPException(status_code=409, detail=f"{winner.capitalize()} has won.")

    if all(game_board[0][column] is not None for column in range(COLUMNS)):
        raise HTTPException(status_code=409, detail="The board is full.")

    for row in range(ROWS - 1, -1, -1):
        if game_board[row][move.column] is None:
            game_board[row][move.column] = current_player
            if find_winner() is None:
                current_player = (
                    SECOND_PLAYER if current_player == FIRST_PLAYER else FIRST_PLAYER
                )
            return current_game_state()

    raise HTTPException(status_code=409, detail="That column is full.")


@app.delete("/game", response_model=GameState, tags=["game"])
async def reset_game() -> GameState:
    """Clear every cell and return the turn to the first player."""

    global current_player

    for row in game_board:
        row[:] = [None] * COLUMNS
    current_player = FIRST_PLAYER

    return current_game_state()
