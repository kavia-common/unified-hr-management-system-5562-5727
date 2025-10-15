#!/usr/bin/env bash
# Entrypoint script for hrms_database readiness service.
# - Initializes the SQLite DB (respects REACT_APP_SQLITE_DB_PATH if provided)
# - Starts the FastAPI/uvicorn server on port 5001 (or $PORT)

set -euo pipefail

# Ensure python dependencies are installed in the environment.
# Note: In CI environment, dependencies are expected to be pre-installed in the image.
# Uncomment if needed:
# pip install --no-cache-dir fastapi uvicorn pydantic

echo "Initializing SQLite database..."
python3 "$(dirname "$0")/init_db.py"

echo "Starting readiness service on port ${PORT:-5001}..."
exec python3 "$(dirname "$0")/server.py"
