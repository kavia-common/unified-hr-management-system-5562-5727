#!/usr/bin/env python3
"""Initialize SQLite database for hrms_database

This script now resolves the SQLite DB path using the same precedence as the health server:
1) DATABASE_URL (if starts with sqlite://)
2) SQLITE_DB_PATH
3) BACKEND_SQLITE_DB_PATH
4) REACT_APP_SQLITE_DB_PATH
5) default myapp.db

It ensures the directory exists, creates the DB if missing, initializes basic schema,
and writes non-sensitive connection info and db_visualizer/sqlite.env for convenience.
"""

import os
import sqlite3
from typing import Optional, Tuple

DEFAULT_DB_FILENAME = "myapp.db"

def _extract_path_from_database_url(database_url: str) -> Optional[str]:
    """Extract a filesystem path from sqlite DATABASE_URL, or None if not sqlite://."""
    if not database_url:
        return None
    lowered = database_url.strip().lower()
    if not lowered.startswith("sqlite://"):
        return None
    raw_path = database_url.strip()[9:]
    if raw_path.startswith("///"):  # sqlite:////abs/path -> keep /abs/path
        return raw_path[2:]
    if raw_path.startswith("//"):
        return raw_path[1:]
    if raw_path.startswith("/"):
        return raw_path
    return raw_path  # relative

def resolve_sqlite_path() -> Tuple[str, str]:
    """Resolve SQLite file path following the same precedence as app.py."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    path_from_url = _extract_path_from_database_url(database_url)
    if path_from_url:
        return path_from_url, "DATABASE_URL"
    alias_path = os.getenv("SQLITE_DB_PATH", "").strip()
    if alias_path:
        return alias_path, "SQLITE_DB_PATH"
    backend_path = os.getenv("BACKEND_SQLITE_DB_PATH", "").strip()
    if backend_path:
        return backend_path, "BACKEND_SQLITE_DB_PATH"
    frontend_path = os.getenv("REACT_APP_SQLITE_DB_PATH", "").strip()
    if frontend_path:
        return frontend_path, "REACT_APP_SQLITE_DB_PATH"
    return DEFAULT_DB_FILENAME, "<default>"

def ensure_db_path(db_path: str) -> Tuple[bool, bool]:
    """Ensure parent dir exists and create empty DB if missing. Returns (dir_created, file_created)."""
    if not db_path:
        return False, False
    dir_created = False
    file_created = False
    parent = os.path.dirname(db_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
        dir_created = True
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        finally:
            conn.close()
        file_created = True
    return dir_created, file_created

def main():
    print("Starting SQLite setup...")
    db_path, source = resolve_sqlite_path()
    masked = f"{'abs' if os.path.isabs(db_path) else 'rel'}::{os.path.basename(db_path) or db_path}"

    if not db_path:
        print("Error: Resolved database path is empty. Aborting.")
        raise SystemExit(1)

    dir_created, file_created = ensure_db_path(db_path)
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
            print(f"SQLite database ready at ({masked}) [source={source}]")
            if dir_created:
                print(" - Created parent directory")
            if file_created:
                print(" - Created new database file")
        except Exception as e:
            print(f"Warning: Database exists but may be corrupted: {type(e).__name__}")
    else:
        print(f"Creating new SQLite database at ({masked}) [source={source}]")

    # Initialize schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)", ("project_name", "hrms_database"))
    cursor.execute("INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)", ("version", "0.1.0"))
    cursor.execute("INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)", ("author", "John Doe"))
    cursor.execute("INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)", ("description", ""))

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    table_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM app_info")
    record_count = cursor.fetchone()[0]
    conn.close()

    # Save connection info (non-sensitive)
    try:
        with open("db_connection.txt", "w") as f:
            f.write("# SQLite connection methods:\n")
            f.write(f"# Python: sqlite3.connect('{os.path.basename(db_path)}')\n")
            f.write(f"# Connection string: sqlite:///{db_path}\n")
            f.write(f"# File path: {db_path}\n")
        print("Connection information saved to db_connection.txt")
    except Exception as e:
        print(f"Warning: Could not save connection info: {type(e).__name__}")

    # Ensure db_visualizer dir exists and write sqlite.env for the viewer
    try:
        os.makedirs("db_visualizer", exist_ok=True)
        with open("db_visualizer/sqlite.env", "w") as f:
            f.write(f'export SQLITE_DB="{db_path}"\n')
        print("Environment variables saved to db_visualizer/sqlite.env")
    except Exception as e:
        print(f"Warning: Could not save environment variables: {type(e).__name__}")

    print("\nSQLite setup complete!")
    print(f"Database: {os.path.basename(db_path)}")
    print(f"Source Env: {source}")
    print("")
    print("To use with Node.js viewer, run: source db_visualizer/sqlite.env")
    print("")
    print("Database statistics:")
    print(f"  Tables: {table_count}")
    print(f"  App info records: {record_count}")

    # Optional: hint if sqlite3 CLI present
    try:
        import subprocess
        result = subprocess.run(['which', 'sqlite3'], capture_output=True, text=True)
        if result.returncode == 0:
            print("")
            print("SQLite CLI is available. You can also use:")
            print(f"  sqlite3 {db_path}")
    except Exception:
        pass

    print("\nScript completed successfully.")

if __name__ == "__main__":
    main()
