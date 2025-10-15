# DB Visualizer

This optional Node/Express utility can view database tables. It must not run on port 5001 as that port is reserved for the hrms_database FastAPI health server.

- Default port: 5002 (can be overridden with PORT env variable)
- Install deps and start:
  cd hrms_database/db_visualizer && npm install --production && PORT=5002 npm start
- Or use helper script:
  ./hrms_database/db_visualizer/start_visualizer.sh

The SQLite DB path is written by init_db.py into sqlite.env:
  source hrms_database/db_visualizer/sqlite.env

Environment vars:
- SQLITE_DB: absolute path to SQLite database file

Operational notes:
- Do NOT use port 5001. The visualizer refuses to start with PORT=5001 to avoid collision with the FastAPI health server.
