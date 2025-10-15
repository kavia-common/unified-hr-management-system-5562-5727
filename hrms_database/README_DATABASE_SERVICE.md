# HRMS Database Readiness Service (SQLite)

This folder hosts the SQLite database assets and a lightweight HTTP service to satisfy the platform's readiness expectations.

## What it does

- Starts a FastAPI server listening on port 5001 (configurable via `PORT`).
- Exposes the following endpoints:
  - `GET /` and `GET /healthz`: liveness checks, return 200 if the service is up.
  - `GET /readiness`: readiness check, opens the SQLite DB and runs a trivial query; returns 200 when ready.
- Ensures the SQLite DB file exists on startup. Creates the directory and initializes a minimal schema if the file is missing.

## Environment Variables

- `REACT_APP_SQLITE_DB_PATH` (required): absolute path to the SQLite database file.
  - Fallback to parseable SQLite path in `REACT_APP_DATABASE_URL` or `DATABASE_URL` if defined.
  - Final fallback uses local `myapp.db` under this directory.
- `PORT` (optional): port to bind the HTTP service; default is `5001`.

Note: Do not commit secrets in code. Provide values via orchestrator-managed `.env`.

## Running locally

```bash
# Example: set DB path and port
export REACT_APP_SQLITE_DB_PATH="$(pwd)/myapp.db"
export PORT=5001

# Install runtime dependencies (if not already available)
# pip install fastapi uvicorn pydantic

# Start service
python server.py
```

Then open:
- http://localhost:5001/
- http://localhost:5001/healthz
- http://localhost:5001/readiness

## Logging

Logs are structured JSON at INFO level. No sensitive data is logged.

## Notes

- The service does not expose database operations—only liveness/readiness checks.
- The backend should continue to connect to the SQLite file directly using its own driver.
