# HRMS Database (SQLite) Container

This container packages the SQLite database and exposes a lightweight health server so orchestrators can detect readiness on a TCP port.

- Health server: FastAPI via Uvicorn
- Port: 5001 (configurable with HEALTH_SERVER_PORT)
- Endpoints:
  - GET /live -> liveness
  - GET /ready -> readiness (checks SQLite file presence/access)
  - GET /health -> combined status

Environment variables (configure via orchestrator):
- DATABASE_URL (preferred for backend): sqlite:////absolute/path/to/myapp.db
- BACKEND_SQLITE_DB_PATH (alternative): /absolute/path/to/myapp.db
- REACT_APP_SQLITE_DB_PATH (legacy fallback): not recommended for backend use
- HEALTH_SERVER_PORT: default 5001

The backend must point to the same SQLite file. Ensure the path is accessible in the backend container (e.g., via a shared volume or consistent image path).

Security:
- No sensitive paths are logged or returned in responses.
- Do not expose endpoints that return database content.

Startup:
- The image runs `python start_server.py` which launches the health server.
- The `init_db.py` script creates/validates the SQLite database file (`myapp.db`) during build.

Verification:
- curl http://localhost:5001/health -> 200 when ready
- curl http://localhost:5001/ready -> 200 when DB file is present
