"""HTTP routes for reading offices, agents and the full scheduled-task prompt."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.loader import Office, build_prompt, list_offices, load_office

router = APIRouter(prefix="/offices", tags=["offices"])


def _office(name: str) -> Office:
    try:
        return load_office(name)
    except KeyError:
        raise HTTPException(404, f"No office named '{name}'")


@router.get("")
def offices() -> list[str]:
    """Every office in agents/."""
    return list_offices()


@router.get("/{office}")
def office(office: str) -> dict:
    """An office's frontmatter and its agents' frontmatter."""
    o = _office(office)
    return {"name": o.name, "meta": o.meta, "agents": {k: a.meta for k, a in o.agents.items()}}


@router.get("/{office}/agents/{agent}")
def agent(office: str, agent: str) -> dict:
    """One agent's frontmatter and prompt text."""
    a = _office(office).agents.get(agent)
    if a is None:
        raise HTTPException(404, f"No agent named '{agent}' in '{office}'")
    return {"meta": a.meta, "body": a.body}


@router.get("/{office}/prompt", response_class=PlainTextResponse)
def prompt(office: str) -> str:
    """The full prompt to paste into the office's scheduled task."""
    return build_prompt(_office(office))
