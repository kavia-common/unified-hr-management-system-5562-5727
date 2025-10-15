"""
Entrypoint script to run the FastAPI health service using Uvicorn.

This script ensures the service binds to 0.0.0.0:5001 and logs concisely.
"""

import os
import sys
import uvicorn

if __name__ == "__main__":
    # Allow override via env var if needed; default to 5001 per requirement
    port_str = os.getenv("HEALTH_SERVER_PORT", "5001")
    try:
        port = int(port_str)
    except ValueError:
        print("Invalid HEALTH_SERVER_PORT; defaulting to 5001", file=sys.stderr)
        port = 5001

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1,
        log_level="info",
    )
