# unified-hr-management-system-5562-5727

Database container (SQLite) readiness:
- A lightweight FastAPI service is included under `hrms_database/server.py` to bind port 5001 and expose health endpoints.
- Endpoints:
  - `GET /` and `GET /healthz`: liveness checks
  - `GET /readiness`: verifies SQLite connectivity
- Configure DB path with `REACT_APP_SQLITE_DB_PATH`. The service will create the DB file if missing.
- Example env file provided at `hrms_database/.env.example`.