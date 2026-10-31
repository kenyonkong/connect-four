import { useCallback, useEffect, useState } from 'react'
import './App.css'

const API_BASE_URL = '/api'

function App() {
  const [game, setGame] = useState(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [pendingColumn, setPendingColumn] = useState(null)
  const [isResetting, setIsResetting] = useState(false)

  const loadGame = useCallback(async (signal) => {
    try {
      const response = await fetch(`${API_BASE_URL}/game`, { signal })
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `The API returned HTTP ${response.status}.`)
      }

      setGame(data)
      setError('')
    } catch (requestError) {
      if (requestError.name !== 'AbortError') {
        setError(requestError.message || 'Unable to load the game.')
      }
    } finally {
      if (!signal?.aborted) {
        setIsLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    // Loading the API state on mount is intentional external synchronization.
    // oxlint-disable-next-line react/set-state-in-effect
    loadGame(controller.signal)

    return () => controller.abort()
  }, [loadGame])

  const dropPiece = async (column) => {
    setPendingColumn(column)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/game`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ column }),
      })
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `The API returned HTTP ${response.status}.`)
      }

      setGame(data)
    } catch (requestError) {
      setError(requestError.message || 'Unable to place the piece.')
    } finally {
      setPendingColumn(null)
    }
  }

  const retry = () => {
    setIsLoading(true)
    loadGame()
  }

  const resetGame = async () => {
    setIsResetting(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/game`, { method: 'DELETE' })
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || `The API returned HTTP ${response.status}.`)
      }

      setGame(data)
    } catch (requestError) {
      setError(requestError.message || 'Unable to reset the game.')
    } finally {
      setIsResetting(false)
    }
  }

  const fullColumns = new Set(game?.full_columns ?? [])
  const gameOver = Boolean(game?.winner || game?.is_full)

  return (
    <main className="page-shell">
      <header className="game-header">
        <div>
          <p className="eyebrow">Two-player game</p>
          <h1>Connect Four</h1>
        </div>
        <div className="game-controls">
          <div
            className={`turn-indicator turn-indicator--${
              game?.winner ?? (game?.is_full ? 'full' : (game?.current_player ?? 'red'))
            }`}
            aria-live="polite"
          >
            <span className="turn-piece" aria-hidden="true" />
            <div>
              <small>{gameOver ? 'Game status' : 'Current turn'}</small>
              <strong>
                {game?.winner
                  ? `${game.winner} wins`
                  : game?.is_full
                    ? 'Draw'
                    : (game?.current_player ?? 'Loading')}
              </strong>
            </div>
          </div>
          <button
            type="button"
            className="reset-button"
            onClick={resetGame}
            disabled={!game || isResetting || pendingColumn !== null}
          >
            {isResetting ? 'Resetting...' : 'Reset game'}
          </button>
        </div>
      </header>

      <p className="instructions">
        Red and yellow alternate automatically. Choose a column and the current
        player's piece will fall to the lowest available space.
      </p>

      {isLoading && <p className="notice">Loading the board...</p>}

      {error && (
        <div className="error-message" role="alert">
          <span>{error}</span>
          {!game && (
            <button type="button" className="retry-button" onClick={retry}>
              Try again
            </button>
          )}
        </div>
      )}

      {game && (
        <section className="game" aria-label="Connect Four game">
          {game.winner ? (
            <p className={`outcome-message outcome-message--${game.winner}`} role="status">
              <strong>{game.winner} wins!</strong> Reset the game to play again.
            </p>
          ) : game.is_full ? (
            <p className="outcome-message" role="status">
              <strong>Draw.</strong> The board is full with no winner. Reset to play
              again.
            </p>
          ) : null}
          <div
            className="column-actions"
            style={{ gridTemplateColumns: `repeat(${game.columns}, 1fr)` }}
          >
            {Array.from({ length: game.columns }, (_, column) => {
              const isFull = fullColumns.has(column)
              const isPending = pendingColumn === column

              return (
                <button
                  type="button"
                  className="drop-button"
                  key={column}
                  onClick={() => dropPiece(column)}
                  disabled={
                    gameOver || isFull || pendingColumn !== null || isResetting
                  }
                  aria-label={
                    isFull
                      ? `Column ${column + 1} is full`
                      : `Drop a ${game.current_player} piece in column ${column + 1}`
                  }
                >
                  <span>{isPending ? '...' : column + 1}</span>
                  <small>{isFull ? 'Full' : 'Drop'}</small>
                </button>
              )
            })}
          </div>

          <div
            className="board"
            role="grid"
            aria-label={`${game.rows} row by ${game.columns} column board`}
            style={{ gridTemplateColumns: `repeat(${game.columns}, 1fr)` }}
          >
            {game.board.map((row, rowIndex) =>
              row.map((cell, columnIndex) => (
                <div
                  className={`cell${cell ? ` cell--${cell}` : ''}`}
                  key={`${rowIndex}-${columnIndex}`}
                  role="gridcell"
                  aria-label={`Row ${rowIndex + 1}, column ${columnIndex + 1}: ${
                    cell ? `${cell} piece` : 'empty'
                  }`}
                >
                  <span aria-hidden="true" />
                </div>
              )),
            )}
          </div>
        </section>
      )}

      <p className="persistence-note">
        The board is saved in backend memory and survives page refreshes. Restarting
        the backend starts a new board.
      </p>
    </main>
  )
}

export default App
