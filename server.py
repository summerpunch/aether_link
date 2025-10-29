import uvicorn
import os

if __name__ == "__main__":
    reload = os.getenv("RELOAD", "true").lower() == "true"
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
        log_level="info",
        h11_max_incomplete_event_size=2 * 1024 * 1024,
    )
