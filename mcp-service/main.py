"""FastAPI entry point: normal web routes plus the MCP server at /mcp.

Run locally:
    ./start.sh        (or: python -m uvicorn main:app --port 8000 --reload)
"""

from fastapi import FastAPI

from app.server import mcp

# MCP over HTTP, served at /mcp
mcp_app = mcp.http_app(path="/mcp")

# FastAPI must run the MCP app's lifespan, or MCP requests fail
app = FastAPI(title="mcp-service", lifespan=mcp_app.lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple check that the service is up."""
    return {"status": "ok"}


# Mounted last so the FastAPI routes above are matched first
app.mount("/", mcp_app)
