#!/usr/bin/env python3
"""
Lightweight HTTP health/readiness service for the hrms_database (SQLite) container.

Purpose:
- Bind an HTTP server to port 5001 so the preview system can detect readiness.
- Provide /, /healthz, and /readiness endpoints.
- Manage SQLite initialization using an environment-configured path.
- Add minimal structured logging and robust error handling.

Target language/runtime:
- Python 3.10+
Frameworks/libraries:
- FastAPI ^0.110 (for HTTP server)
- Uvicorn ^0.23 (for ASGI server)
- sqlite3 from stdlib
- pydantic for settings validation

Environment variables (must be provided via .env by orchestrator):
- REACT_APP_SQLITE_DB_PATH: Full path to SQLite .db file.
  Fallbacks: DATABASE_URL and REACT_APP_DATABASE_URL are parsed for sqlite path if provided.
- PORT: Optional; defaults to 5001

Security notes:
- No sensitive information is logged.
- No DB credentials needed for SQLite.
"""

import json
import logging
import os
import re
import sqlite3
from contextlib import closing
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import uvicorn


# -----------------------------------------------------------------------------
# Configuration and Settings
# -----------------------------------------------------------------------------

class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    # PUBLIC_INTERFACE
    sqlite_db_path: str = Field(..., description="Absolute path to the SQLite database file.")
    # PUBLIC_INTERFACE
    port: int = Field(5001, description="Port to bind the HTTP readiness service to.")

    @validator("sqlite_db_path")
    def validate_sqlite_db_path(cls, v: str) -> str:
        if not v:
            raise ValueError("sqlite_db_path must not be empty")
        # Normalize to absolute path for clarity
        return os.path.abspath(v)

    @validator("port")
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v


def parse_sqlite_from_url(url: str) -> Optional[str]:
    """
    Attempt to parse a SQLite file path from a DATABASE_URL-like string.
    Supports forms like:
      - sqlite:///absolute/path/to.db
      - sqlite:////absolute/path/to.db
      - file:/absolute/path/to.db
    Returns absolute path if parseable, else None.
    """
    if not url:
        return None
    try:
        # Common patterns for sqlite URL
        # sqlite:////absolute/path -> starts with sqlite: followed by 3 or 4 slashes and path
        if url.startswith("sqlite:///"):
            # May be 'sqlite:////abs' with 4 slashes meaning absolute path
            # Normalize multiple slashes after scheme
            path = re.sub(r"^sqlite:/+","/", url).strip()
            return os.path.abspath(path)
        if url.startswith("file:/"):
            path = url[len("file:") :]
            return os.path.abspath(path)
        # Sometimes received as plain file path
        if url.endswith(".db") and ("/" in url or "\\" in url):
            return os.path.abspath(url)
    except Exception:
        return None
    return None


def load_settings() -> Settings:
    """
    Load settings from environment variables with fallbacks. We do not read/write .env files here.
    Required:
    - REACT_APP_SQLITE_DB_PATH or a parseable sqlite path in REACT_APP_DATABASE_URL/DATABASE_URL
    """
    # Try primary env var for sqlite path
    sqlite_path = os.environ.get("REACT_APP_SQLITE_DB_PATH", "").strip()

    # Fallback: try DATABASE_URL variants
    if not sqlite_path:
        for key in ("REACT_APP_DATABASE_URL", "DATABASE_URL"):
            url = os.environ.get(key, "").strip()
            parsed = parse_sqlite_from_url(url)
            if parsed:
                sqlite_path = parsed
                break

    # As a final fallback, use a local file 'myapp.db' inside this folder (kept for backwards compatibility).
    # This still respects the "no hardcoded secrets" rule and does not expose credentials.
    if not sqlite_path:
        sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "myapp.db"))

    # PORT
    port_env = os.environ.get("PORT", "5001").strip()
    try:
        port_val = int(port_env)
    except ValueError:
        port_val = 5001

    return Settings(sqlite_db_path=sqlite_path, port=port_val)


# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------

def configure_logging() -> logging.Logger:
    """
    Configure structured logging with INFO as default.
    Avoid logging sensitive information.
    """
    logger = logging.getLogger("hrms_database_readiness")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
    )
    handler.setFormatter(formatter)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


logger = configure_logging()


# -----------------------------------------------------------------------------
# Database utilities
# -----------------------------------------------------------------------------

def ensure_db_file(settings: Settings) -> None:
    """
    Ensure the SQLite database file exists. If the directory does not exist, create it.
    If the file does not exist, create an empty database and a basic app_info table to validate readiness.
    """
    db_path = settings.sqlite_db_path
    db_dir = os.path.dirname(db_path)

    # Create directory if missing
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created SQLite directory: {db_dir}")

    # If DB doesn't exist, create it with a minimal schema
    if not os.path.exists(db_path):
        logger.info(f"SQLite DB not found at {db_path}. Initializing new database.")
        try:
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.execute(
                    "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
                    ("service", "hrms_database"),
                )
                conn.commit()
        except sqlite3.Error as exc:
            logger.error(f"Failed to initialize SQLite database: {exc}")
            raise
        logger.info("SQLite DB initialized successfully.")


def check_db_readiness(settings: Settings) -> dict:
    """
    Attempt a simple query against the SQLite DB to verify readiness.
    Returns a dict with status and details.
    """
    try:
        with closing(sqlite3.connect(settings.sqlite_db_path, timeout=2.0)) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"ready": True, "db_path": settings.sqlite_db_path}
    except sqlite3.Error as exc:
        return {"ready": False, "error": str(exc), "db_path": settings.sqlite_db_path}


# -----------------------------------------------------------------------------
# FastAPI app and routes
# -----------------------------------------------------------------------------

app = FastAPI(
    title="HRMS Database Readiness Service",
    description=(
        "Health and readiness endpoints for the hrms_database container (SQLite). "
        "Provides basic checks so the platform can determine when the database container is ready. "
        "This service does not expose database operations."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Service health and readiness checks"}
    ],
)

SETTINGS = load_settings()
try:
    ensure_db_file(SETTINGS)
except Exception as exc:
    # Log early failure, but still allow health endpoints to respond with 500
    logger.error(f"Database initialization error: {exc}")


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check", description="Returns 200 if the service is running.")
def root_health() -> JSONResponse:
    """
    Basic liveness probe. Indicates the HTTP service is up.
    """
    payload = {"status": "ok", "service": "hrms_database_readiness"}
    return JSONResponse(status_code=200, content=payload)


# PUBLIC_INTERFACE
@app.get("/healthz", tags=["Health"], summary="Kubernetes-style health check", description="Alias for / that returns 200 if the service is running.")
def k8s_healthz() -> JSONResponse:
    """
    Kubernetes-style health endpoint, returns 200 if process is alive.
    """
    payload = {"status": "ok", "service": "hrms_database_readiness"}
    return JSONResponse(status_code=200, content=payload)


# PUBLIC_INTERFACE
@app.get(
    "/readiness",
    tags=["Health"],
    summary="Readiness Check",
    description="Verifies SQLite database connectivity using a simple query. Returns 200 if ready.",
)
def readiness_check() -> JSONResponse:
    """
    Readiness probe that ensures we can open the SQLite DB and run a trivial query.
    """
    result = check_db_readiness(SETTINGS)
    if result.get("ready"):
        logger.info(json.dumps({"event": "readiness_ok", "db_path": SETTINGS.sqlite_db_path}))
        return JSONResponse(status_code=200, content={"status": "ready", "details": {"db_path": SETTINGS.sqlite_db_path}})
    logger.error(json.dumps({"event": "readiness_failed", "details": result}))
    return JSONResponse(status_code=503, content={"status": "not_ready", "details": result})


def main() -> None:
    """
    Entrypoint to run the ASGI server using uvicorn.
    Binds to 0.0.0.0 on configured port (default 5001).
    """
    # Bind explicitly to 0.0.0.0 so container exposes the port correctly
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=SETTINGS.port,
        log_level="info",
        reload=False,
        workers=1,
    )


if __name__ == "__main__":
    main()
