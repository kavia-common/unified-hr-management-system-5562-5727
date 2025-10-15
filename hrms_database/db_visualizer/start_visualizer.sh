#!/usr/bin/env bash
# Optional helper to run the db_visualizer without interfering with the FastAPI health server.
# - Installs npm dependencies if missing
# - Uses PORT=5002 by default (can be overridden)
# - Runs in foreground (caller can background it with & if needed)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default to port 5002 to avoid clashing with FastAPI health server on 5001
export PORT="${PORT:-5002}"

echo "Installing db_visualizer dependencies (production only)..."
if command -v npm >/dev/null 2>&1; then
  npm install --production
else
  echo "Error: npm is not installed in this image/environment." >&2
  echo "Install Node.js/npm or run the visualizer externally." >&2
  exit 1
fi

echo "Starting db_visualizer on 0.0.0.0:${PORT} (health server remains on 5001)..."
npm start
