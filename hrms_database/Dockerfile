# Minimal Dockerfile for hrms_database container
# Purpose: Provide a runtime for SQLite database files and expose a health server on port 5001.

FROM python:3.11-slim

# Prevent interactive prompts
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# System dependencies (sqlite3 CLI optional but small; ca-certificates for HTTPS if needed)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    sqlite3 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy code and database files
COPY . /app

# Install required Python packages
# Keep dependency list minimal for faster builds and lower attack surface.
RUN pip install --no-cache-dir fastapi==0.110.0 uvicorn==0.29.0 pydantic==2.6.4

# Initialize SQLite DB if not present
# This is safe to run at build time as well; DB will be part of image for preview convenience.
# In a real deployment, you might mount a volume and run init at container start.
RUN python init_db.py || true

# Expose health server port
EXPOSE 5001

# Environment variables (no secrets); allow overrides at runtime
# DATABASE_URL may be set by orchestrator for absolute path; otherwise default resolves to myapp.db.
ENV HEALTH_SERVER_PORT=5001

# Start the health server
CMD ["python", "start_server.py"]
