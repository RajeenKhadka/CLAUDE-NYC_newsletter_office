"""FastAPI entry point for the agent service: serves each office's agent prompts.

Run locally:
    ./start.sh        (or: python -m uvicorn main:app --port 8001 --reload)
"""

from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="agent-service")


@app.get("/health")
def health() -> dict[str, str]:
    """Simple check that the service is up."""
    return {"status": "ok"}


app.include_router(router)
