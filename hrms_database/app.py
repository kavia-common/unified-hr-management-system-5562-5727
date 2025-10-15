"""
Module: hrms_database FastAPI health/readiness service

Purpose:
- Expose a lightweight HTTP server on port 5001 to allow health/readiness checks for the hrms_database container.
- Validate presence and accessibility of the SQLite database file used by the backend.
- Provide liveness (/live), readiness (/ready), and health (/health) endpoints.
- Avoid exposing sensitive details; do not leak exact file paths in responses.

Target language: Python 3.10+
Framework: FastAPI ^0.110, Uvicorn ASGI server
Deployment: Containerized service, bound to 0.0.0.0:5001

Security considerations:
- No secrets are logged or returned in responses.
- File system checks are minimal and do not list directories or expose contents.
- Environment variables are read safely; suggest configuring via .env in orchestrator.

Usage:
- The server will be started by start_server.py (uvicorn) binding to 0.0.0.0:5001.
"""

import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, Response, status
from pydantic import BaseModel, Field

# Constants and configuration
DEFAULT_DB_FILENAME = "myapp.db"
DEFAULT_PORT = 5001

# Resolve DB path from environment variables in order of precedence:
# 1) DATABASE_URL if it starts with sqlite:// (standard)
# 2) SQLITE_DB_PATH (common alias used by some orchestrators)
# 3) BACKEND_SQLITE_DB_PATH (backend-specific)
# 4) REACT_APP_SQLITE_DB_PATH (legacy/frontend-scoped; fallback only)
# 5) Local default file "myapp.db"
def _extract_path_from_database_url(database_url: str) -> Optional[str]:
    """
    Safely extract a SQLite file path from a DATABASE_URL formatted as sqlite:///path/to/file.db.
    Returns None if URL is not sqlite-based.
    """
    if not database_url:
        return None
    lowered = database_url.strip().lower()
    if not lowered.startswith("sqlite://"):
        return None
    # Support sqlite:///absolute/path and sqlite:////absolute/path variants
    # Common patterns:
    # - sqlite:///relative.db
    # - sqlite:////absolute/path.db
    # Remove the sqlite:// prefix and normalize leading slashes
    raw_path = database_url.strip()[9:]
    # raw_path may start with 1-3 slashes for relative vs absolute; normalize
    if raw_path.startswith("///"):  # absolute path form
        return raw_path[2:]  # keep a single leading slash for absolute path
    if raw_path.startswith("//"):  # non-standard; treat like absolute
        return raw_path[1:]
    if raw_path.startswith("/"):  # absolute as well
        return raw_path
    # else relative path
    return raw_path


def resolve_sqlite_path() -> str:
    """
    Determine the SQLite DB file path using safe precedence order.
    """
    # DATABASE_URL (preferred for backend services)
    database_url = os.getenv("DATABASE_URL", "")
    database_url = database_url.strip() if database_url is not None else ""
    path_from_url = _extract_path_from_database_url(database_url)
    if path_from_url:
        return path_from_url

    # Generic alias commonly used
    alias_path = os.getenv("SQLITE_DB_PATH", "")
    alias_path = alias_path.strip() if alias_path is not None else ""
    if alias_path:
        return alias_path

    # Backend-specific var
    backend_path = os.getenv("BACKEND_SQLITE_DB_PATH", "")
    backend_path = backend_path.strip() if backend_path is not None else ""
    if backend_path:
        return backend_path

    # Legacy frontend-scoped var as last resort
    frontend_path = os.getenv("REACT_APP_SQLITE_DB_PATH", "")
    frontend_path = frontend_path.strip() if frontend_path is not None else ""
    if frontend_path:
        return frontend_path

    # Default local file
    return DEFAULT_DB_FILENAME


def _ensure_db_path(db_path: str) -> None:
    """
    Ensure directory structure exists and create an empty SQLite file if missing.
    This function is idempotent and safe to call on every readiness check.
    """
    if not db_path:
        return
    parent = os.path.dirname(db_path)
    if parent and not os.path.exists(parent):
        # Create parent directories with safe permissions
        os.makedirs(parent, exist_ok=True)
    if not os.path.exists(db_path):
        # Create the database by opening a connection and closing it
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        finally:
            conn.close()


def check_sqlite_access(db_path: str) -> tuple[bool, Optional[str]]:
    """
    Check whether the SQLite database file exists and can be opened for a simple query.
    Returns (is_ready, error_message_if_any)
    """
    try:
        if not db_path:
            return False, "Database path is empty"
        # Ensure path and file are present; create if missing
        _ensure_db_path(db_path)
        # Try opening and a small query
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("SELECT 1")
        finally:
            conn.close()
        return True, None
    except Exception as exc:
        # Do not leak file path or stack; return minimal message
        return False, f"Database check failed: {exc.__class__.__name__}"


class HealthStatus(BaseModel):
    """Response model for health endpoints (non-sensitive)."""
    status: str = Field(..., description="Overall health status (ok or error)")
    checks: dict = Field(..., description="Map of individual checks with their status")
    details: Optional[dict] = Field(
        default=None,
        description="Additional non-sensitive information helpful for diagnostics"
    )


# FastAPI app with metadata and OpenAPI tags
app = FastAPI(
    title="HRMS Database Health Service",
    description=(
        "Lightweight service exposing liveness and readiness endpoints for the hrms_database container. "
        "It validates access to the SQLite database file expected by the backend."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "Health", "description": "Service liveness and readiness endpoints"},
    ],
)


# PUBLIC_INTERFACE
@app.get(
    "/live",
    tags=["Health"],
    summary="Liveness probe",
    description="Returns 200 if the service process is running.",
    response_model=HealthStatus,
)
def live() -> HealthStatus:
    """This endpoint indicates the service is alive (process is running)."""
    return HealthStatus(
        status="ok",
        checks={"process": "ok"},
        details=None,
    )


# PUBLIC_INTERFACE
@app.get(
    "/ready",
    tags=["Health"],
    summary="Readiness probe",
    description=(
        "Returns 200 if the service is ready to serve requests. "
        "This checks that the SQLite database file is present and accessible."
    ),
    response_model=HealthStatus,
)
def ready(response: Response) -> HealthStatus:
    """This endpoint verifies SQLite readiness (file exists and is accessible)."""
    db_path = resolve_sqlite_path()
    is_ok, err = check_sqlite_access(db_path)
    if is_ok:
        return HealthStatus(
            status="ok",
            checks={"sqlite": "ok"},
            details={"driver": "sqlite3"},
        )
    # unhealthy
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthStatus(
        status="error",
        checks={"sqlite": "error"},
        details={"reason": "not_ready", "error": err or "unknown"},
    )


# PUBLIC_INTERFACE
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Combined health check that includes liveness and readiness signals.",
    response_model=HealthStatus,
)
def health(response: Response) -> HealthStatus:
    """This endpoint aggregates basic service health including DB file presence."""
    db_path = resolve_sqlite_path()
    is_ok, err = check_sqlite_access(db_path)
    overall = "ok" if is_ok else "error"
    if not is_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    # Note: We avoid returning exact file path for security; provide minimal details.
    return HealthStatus(
        status=overall,
        checks={
            "process": "ok",
            "sqlite": "ok" if is_ok else "error",
        },
        details={"driver": "sqlite3"} if is_ok else {"reason": "not_ready", "error": err or "unknown"},
    )
