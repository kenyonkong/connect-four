# Connect Four

This is a two-player Connect Four board with a React/Vite frontend and a FastAPI backend. The 6-row by 7-column board and current turn are held in backend memory, so both survive browser refreshes and reset when the backend process restarts.

## Project structure

```text
.
|-- compose.yaml       Production container stack
|-- frontend/          React + Vite application and Nginx proxy
|   |-- Dockerfile
|   `-- nginx.conf
|-- backend/
|   |-- .venv/         Local Python virtual environment (not committed)
|   |-- Dockerfile
|   |-- main.py        FastAPI application
|   |-- test_main.py   Game API tests
|   |-- requirements.txt
|   `-- requirements-dev.txt
`-- README.md
```

## Prerequisites

- Node.js 20.19+ or 22.12+
- npm
- Python 3.10+
- Docker with Compose (production stack only)

## Request architecture

The browser always uses same-origin `/api` URLs:

```text
Development: Browser -> Vite :5173  -> /api proxy -> FastAPI :8000
Production:  Browser -> Nginx :8080 -> /api proxy -> FastAPI :8000
```

FastAPI keeps its internal routes at `/game`, `/health`, and `/docs`. Vite and Nginx remove the public `/api` prefix when forwarding requests. This avoids browser CORS configuration and keeps the production backend private to the container network.

## Launch the backend

From the project root, open a terminal and run:

### Windows PowerShell

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

If PowerShell blocks activation scripts, activation is optional; run the virtual environment directly instead:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

### macOS or Linux

Create a platform-local virtual environment first if this repository came from Windows:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

The API will be available at <http://localhost:8000>. Interactive API documentation is at <http://localhost:8000/docs>.

## Launch the frontend

Keep the backend running. Open a second terminal from the project root and run:

```powershell
cd frontend
npm install
npm run dev
```

If PowerShell blocks the `npm.ps1` script, use `npm.cmd install` and `npm.cmd run dev` instead.

Open <http://localhost:5173> to use the game board.

The frontend calls the same-origin `/api` path. Vite forwards those requests to `http://127.0.0.1:8000`, so start the backend before the frontend.

## Launch the production stack

From the project root:

```powershell
docker compose up --build
```

Open <http://localhost:8080>. Only Nginx is published to the host; FastAPI is reached through the following same-origin URLs:

- Game API: <http://localhost:8080/api/game>
- Health check: <http://localhost:8080/api/health>
- API documentation: <http://localhost:8080/api/docs>

Stop the stack with `docker compose down`. Because the board is in backend process memory, recreating or restarting the backend container resets the game.

## Game API

Columns are zero-based in the API, from `0` through `6`.

The FastAPI routes are shown below. Add the `/api` prefix when accessing them through Vite or Nginx.

- `GET /game` returns the current board, current player, full columns, `is_full` status, and `winner`.
- `POST /game` accepts `{"column": 0}`, assigns the current player's red or yellow piece, drops it into the lowest available row, checks for four connected pieces, and advances the turn only if nobody won.
- `DELETE /game` clears every cell and returns the turn to red.
- The backend assigns players, so clients cannot choose a player or a specific row.
- Four matching pieces horizontally, vertically, or diagonally win the game. Further moves return HTTP `409`.
- A full board without a winner is a draw. Invalid requests return HTTP `422`. Rejected moves do not advance the turn.

With the backend running, inspect the current state:

```powershell
Invoke-RestMethod http://localhost:8000/game
```

Place a piece in the first column:

```powershell
Invoke-RestMethod http://localhost:8000/game `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"column":0}'
```

Refresh <http://localhost:5173> and confirm the pieces and current player remain unchanged.

## Run the tests

Install the test dependencies and run the backend tests:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Verify the frontend:

```powershell
cd frontend
npm run lint
npm run build
```
