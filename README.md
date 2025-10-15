# unified-hr-management-system-5562-5727

## hrms_database container health/readiness

The hrms_database container now includes a lightweight FastAPI health service listening on port 5001. It validates that the SQLite database file exists and can be opened.

- Service: FastAPI (uvicorn)
- Port: 5001
- Endpoints:
  - GET /live -> 200 when the process is running
  - GET /ready -> 200 when the SQLite file is present and accessible; 503 otherwise
  - GET /health -> combined health; 200 when healthy; 503 otherwise

Environment variables (configure via orchestrator, do not hardcode):
- DATABASE_URL (preferred): sqlite:/// style URL, e.g., sqlite:////app/myapp.db
- BACKEND_SQLITE_DB_PATH: direct file path, e.g., /app/myapp.db
- REACT_APP_SQLITE_DB_PATH: legacy/fallback only
- HEALTH_SERVER_PORT: default 5001

The backend should use the same SQLite path. A .env.example is provided in hrms_database/.env.example.