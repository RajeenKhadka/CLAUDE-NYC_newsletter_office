"""Tests for the changeset runner and the NYC Today schema.

The database tests need a throwaway Postgres (e.g. a Neon branch) in TEST_DATABASE_URL.
They drop and recreate the nyc_today schema, so never point it at real data.
"""

import os
from pathlib import Path

import psycopg
import pytest

from migrate import MIGRATIONS_DIR, changesets, checksum, migrate, status


def test_changesets_sorted_by_number(tmp_path: Path) -> None:
    for name in ["002_b.sql", "001_a.sql", "010_c.sql"]:
        (tmp_path / name).write_text("select 1;")
    assert [p.name for p in changesets(tmp_path)] == ["001_a.sql", "002_b.sql", "010_c.sql"]


@pytest.mark.parametrize("bad", ["1_a.sql", "001-a.sql", "001_A.sql", "init.sql"])
def test_bad_names_rejected(tmp_path: Path, bad: str) -> None:
    (tmp_path / bad).write_text("select 1;")
    with pytest.raises(ValueError):
        changesets(tmp_path)


def test_duplicate_numbers_rejected(tmp_path: Path) -> None:
    (tmp_path / "001_a.sql").write_text("select 1;")
    (tmp_path / "001_b.sql").write_text("select 1;")
    with pytest.raises(ValueError, match="share the number"):
        changesets(tmp_path)


def test_checksum_ignores_line_endings(tmp_path: Path) -> None:
    a, b = tmp_path / "a.sql", tmp_path / "b.sql"
    a.write_bytes(b"select 1;\nselect 2;\n")
    b.write_bytes(b"select 1;\r\nselect 2;\r\n")
    assert checksum(a) == checksum(b)


def test_repo_changesets_are_valid() -> None:
    assert changesets(MIGRATIONS_DIR)


# ---------- database tests ----------

DB_URL = os.environ.get("TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not DB_URL, reason="set TEST_DATABASE_URL to a throwaway Postgres")


@pytest.fixture
def conn():
    with psycopg.connect(DB_URL, autocommit=True) as c:
        c.execute("drop schema if exists nyc_today cascade")
        c.execute("drop table if exists public.schema_migrations")
        yield c
        c.execute("drop schema if exists nyc_today cascade")
        c.execute("drop table if exists public.schema_migrations")


RUN = {
    "run_id": "run-1", "date": "2026-10-21", "agent": "rio", "target": None, "model": "opus",
    "items": 1, "total_tokens": 1000, "tool_uses": 10, "duration_ms": 5000,
    "finished_at": "2026-10-21T12:00:00Z",
}
ITEM = {
    "run_id": "run-1", "ref": "rio:0", "date": "2026-10-21", "agent": "rio", "section": "Happy Hours",
    "name": "Mermaid Oyster Bar", "venue": "Mermaid Oyster Bar",
    "url": "https://www.themermaidnyc.com/mermaid-oyster-bar-menus/",
    "summary": "$2 oysters and clams (min. 6), $8 draft beer, $10 wine, $12 cocktails",
    "neighborhood": "Greenwich Village", "borough": "Manhattan", "time": "4:30–6pm", "price": "$$",
    "address": "89 MacDougal St", "condition": None,
    "overview": "Greenwich Village seafood restaurant and oyster bar.",
    "confirmed_on": "venue menus page", "source_date": None, "verdict": None,
}


def insert(c: psycopg.Connection, table: str, row: dict) -> None:
    cols = ", ".join(row)
    marks = ", ".join(["%s"] * len(row))
    c.execute(f"insert into nyc_today.{table} ({cols}) values ({marks})", list(row.values()))


@needs_db
def test_migrate_is_idempotent(conn) -> None:
    assert migrate(conn) == [p.name for p in changesets()]
    assert migrate(conn) == []
    assert all(state == "applied" for _, state in status(conn))


@needs_db
def test_edited_changeset_refused(conn, tmp_path: Path) -> None:
    f = tmp_path / "001_a.sql"
    f.write_text("select 1;")
    migrate(conn, tmp_path)
    f.write_text("select 2;")
    with pytest.raises(RuntimeError, match="edited"):
        migrate(conn, tmp_path)


@needs_db
def test_good_item_inserts(conn) -> None:
    migrate(conn)
    insert(conn, "runs", RUN)
    insert(conn, "items", ITEM)


@needs_db
@pytest.mark.parametrize(
    "change",
    [
        {"venue": None},                                    # required missing
        {"summary": ""},                                    # required blank
        {"condition": ""},                                  # optional must be NULL, not ''
        {"borough": "NYC"},
        {"price": "$12"},                                   # Happy Hours must use a tier
        {"address": "25 11th Ave, New York, NY 10011"},     # street only
        {"address": "33-16 30th Avenue, Astoria, NY 11103"},
        {"url": "themermaidnyc.com"},
        {"section": "Food"},                                # wrong section for rio
        {"summary": "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen"},
        {"confirmed_on": "x" * 81},
        {"date": "2026-10-22"},                             # must match its run
    ],
)
def test_bad_item_rejected(conn, change: dict) -> None:
    migrate(conn)
    insert(conn, "runs", RUN)
    with pytest.raises(psycopg.errors.IntegrityError):
        insert(conn, "items", {**ITEM, **change})


@needs_db
@pytest.mark.parametrize(
    "price",
    # real Juno prices: Music keeps the price exactly as the venue states it
    ["$35.46–$45.76", "$30 advance, $35 day of show", "$10 suggested donation", "$25 / $40 / $50 / $55", "Free"],
)
def test_music_keeps_exact_price(conn, price: str) -> None:
    migrate(conn)
    insert(conn, "runs", {**RUN, "run_id": "run-2", "agent": "juno"})
    insert(conn, "items", {**ITEM, "run_id": "run-2", "ref": "juno:0", "agent": "juno",
                           "section": "Music", "price": price})


@needs_db
def test_vera_run_needs_target(conn) -> None:
    migrate(conn)
    with pytest.raises(psycopg.errors.IntegrityError):
        insert(conn, "runs", {**RUN, "run_id": "chk-1", "agent": "vera"})
    insert(conn, "runs", {**RUN, "run_id": "chk-1", "agent": "vera", "target": "rio"})
