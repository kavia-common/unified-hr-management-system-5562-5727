# Minimal Dockerfile for hrms_database container
# Purpose: Provide a runtime for SQLite database files and expose a health server on port 5001.
# Note: Do NOT start the optional db_visualizer on port 5001. If you want the visualizer, run it on 5002 separately.

FROM python:3.11-slim

# Prevent interactive prompts
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# System dependencies (sqlite3 CLI optional but small; ca-certificates for HTTPS if needed)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    sqlite3 ca-certificates curl gnupg && \
    rm -rf /var/lib/apt/lists/*

# Copy code and database files
COPY . /app

# Install required Python packages for health server
# Keep dependency list minimal for faster builds and lower attack surface.
RUN pip install --no-cache-dir fastapi==0.110.0 uvicorn==0.29.0 pydantic==2.6.4

# Initialize SQLite DB if not present
# This is safe to run at build time as well; DB will be part of image for preview convenience.
# In a real deployment, you might mount a volume and run init at container start.
RUN python init_db.py || true

# Expose health server port (reserved for FastAPI)
EXPOSE 5001
# Optionally expose db_visualizer port (5002) if you choose to run it manually
EXPOSE 5002

# Environment variables (no secrets); allow overrides at runtime
# DATABASE_URL may be set by orchestrator for absolute path; otherwise default resolves to myapp.db.
ENV HEALTH_SERVER_PORT=5001

# Start ONLY the FastAPI health server on 5001.
# If you wish to run the optional db_visualizer, do so separately, for example:
#   (cd hrms_database/db_visualizer && npm install --production && PORT=5002 npm start &)
# ensuring it never binds to 5001 and does not block the health server readiness.
# Health verification from host (example):
#   curl -sSf http://localhost:5001/health
#   curl -sSf http://localhost:5001/ready
CMD ["python", "start_server.py"]
