# unified-hr-management-system-5562-5727

## hrms_database container health/readiness

The hrms_database container includes a lightweight FastAPI health service listening on port 5001. It validates that the SQLite database file exists and can be opened.

- Service: FastAPI (uvicorn), binds 0.0.0.0:5001 by default via start_server.py
- Port: 5001
- Endpoints:
  - GET /live -> 200 when the process is running
  - GET /ready -> 200 when the SQLite file is present and accessible; 503 otherwise
  - GET /health -> combined health; 200 when healthy; 503 otherwise

Environment variables (configure via orchestrator, do not hardcode):
- DATABASE_URL (preferred): sqlite:/// style URL, e.g., sqlite:////app/myapp.db
- SQLITE_DB_PATH: direct file path alias, e.g., /app/myapp.db
- BACKEND_SQLITE_DB_PATH: direct file path, e.g., /app/myapp.db
- REACT_APP_SQLITE_DB_PATH: legacy/fallback only
- HEALTH_SERVER_PORT: default 5001

Resolution precedence for SQLite path (used consistently by both init_db.py and the health service):
1) DATABASE_URL (only if it starts with sqlite://), else
2) SQLITE_DB_PATH, else
3) BACKEND_SQLITE_DB_PATH, else
4) REACT_APP_SQLITE_DB_PATH, else
5) default local file myapp.db

Behavior:
- The readiness check will create the database folder and initialize an empty DB file if missing, then return 200 once the DB is usable.
- Health responses include non-sensitive diagnostics and logs mask the database path (basename only) to avoid leaking sensitive details.

Visualizer:
- The optional db_visualizer is a Node/Express utility. It must not run on 5001 (reserved for health server).
- Install dependencies once:
  cd hrms_database/db_visualizer && npm install --production
- Run it on a different port (e.g., 5002):
  PORT=5002 npm start
- The init script writes hrms_database/db_visualizer/sqlite.env pointing to the resolved DB path.

The backend should use the same SQLite path. A .env.example is provided in hrms_database/.env.example.