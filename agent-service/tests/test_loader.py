"""Tests for loading agent files and building the scheduled-task prompt."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.loader import build_prompt, list_offices, load_office, parse
from main import app


def test_nyc_today_loads_every_agent() -> None:
    office = load_office("nyc_today")
    assert set(office.agents) == {"rio", "fern", "basil", "juno", "vera", "boss"}


def test_prompt_has_every_agent_and_no_frontmatter() -> None:
    prompt = build_prompt(load_office("nyc_today"))
    for heading in ["=== BRIEF: rio ===", "=== BRIEF: juno ===", "=== VERA'S BRIEF ===", "=== THE BOSS'S BRIEF ==="]:
        assert heading in prompt
    assert "\n---\n" not in prompt and not prompt.startswith("---")


def test_every_office_builds() -> None:
    for name in list_offices():
        assert build_prompt(load_office(name)).strip()


def test_unknown_or_unsafe_office_rejected() -> None:
    for name in ["nope", "../agents", "NYC"]:
        with pytest.raises(KeyError):
            load_office(name)


def test_missing_frontmatter_rejected(tmp_path: Path) -> None:
    p = tmp_path / "rio.md"
    p.write_text("no frontmatter here")
    with pytest.raises(ValueError):
        parse(p)


def test_routes() -> None:
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    assert "nyc_today" in client.get("/offices").json()
    assert client.get("/offices/nyc_today/agents/rio").json()["meta"]["section"] == "Happy Hours"
    assert client.get("/offices/nyc_today/agents/nobody").status_code == 404
    assert client.get("/offices/nyc_today/prompt").text.startswith("You run the")
