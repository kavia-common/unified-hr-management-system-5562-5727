#!/usr/bin/env python3
"""Test SQLite database connection with env-aware DB path."""

import os
import sqlite3
import sys

# Prefer REACT_APP_SQLITE_DB_PATH if provided; fallback to local myapp.db
env_db_path = os.environ.get("REACT_APP_SQLITE_DB_PATH", "").strip()
DB_NAME = os.path.abspath(env_db_path) if env_db_path else os.path.abspath("myapp.db")

try:
    # Check if database file exists
    if not os.path.exists(DB_NAME):
        print(f"Database file '{DB_NAME}' not found")
        sys.exit(1)

    # Connect to database and get version
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT sqlite_version()")
    version = cursor.fetchone()[0]
    conn.close()

    print(f"SQLite version: {version}")
    sys.exit(0)

except sqlite3.Error as e:
    print(f"Connection failed: {e}")
    sys.exit(1)
