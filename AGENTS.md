# AGENTS.md

Guidance for AI coding agents working in this repo.

## Project

NYC Today: a daily NYC newsletter made by a team of Claude agents (an "office"). The repo holds three
independent services. Each has its own `requirements.txt`, its own `.venv`, and runs on its own.
Python 3.13. No shared code between services: import only from inside the service you're in.

## Layout

```
mcp-service/           MCP server (FastMCP served by FastAPI), port 8000
  main.py              FastAPI app: /health + MCP server mounted at /mcp
  app/server.py        Creates the FastMCP instance (`mcp`) and registers every tool
  app/db.py            Postgres connection helper (`get_connection()`)
  app/tools/           Tool modules, plain Python functions grouped by topic
agent-service/         Agent prompts as markdown, served over HTTP, port 8001
  main.py              FastAPI app: /health + /offices routes
  app/loader.py        Reads agents/<office>/*.md (frontmatter + body), builds the full prompt
  app/routes.py        /offices, /offices/{office}, /offices/{office}/agents/{agent}, /offices/{office}/prompt
  agents/<office>/     office.md (orchestration) + one <agent>.md per agent
  web/<office>/        the office page, published as a Claude Artifact (not served here)
db-migration/          SQL changesets; a script, not a server
  migrate.py           Applies migrations/ in order (tracked in public.schema_migrations)
  migrations/          NNN_short_name.sql
.env.example           Copy to .env.local in the repo root; every service loads it
```

## Commands

Run from the repo root. Each script creates the service's `.venv` and installs its requirements.

```bash
./mcp-service/start.sh                   # :8000 (MCP at /mcp, docs at /docs); PORT=9000 to change
./agent-service/start.sh                 # :8001 (offices at /offices)
./db-migration/migrate.sh                # apply pending changesets
./db-migration/migrate.sh --status       # applied / pending / edited
cd <service> && .venv/bin/python -m pytest   # tests for one service
```

## Agents (agent-service)

- One file per agent: `agents/<office>/<id>.md`. Frontmatter `id` must equal the file name.
- `office.md` frontmatter `prompt_order` sets the order agents appear in the stitched prompt.
- `GET /offices/<office>/prompt` is the exact text for the office's scheduled task. Keep agent bodies
  self-contained: the orchestration in `office.md` refers to them by their `=== ... ===` headings.
- Don't change the database document shapes described in `office.md`: the office page reads them.
- A new office is a new folder with its own `office.md`.

## Adding an MCP tool (mcp-service)

1. Write a plain, typed function with a docstring in `app/tools/<topic>.py`.
   The type hints and docstring become the tool's schema and description, so keep them accurate.
2. Register it in `app/server.py`: `mcp.add_tool(<topic>.<fn>)`.
3. Add a test in `tests/test_<topic>.py` that calls the function directly.

Keep tool functions free of FastMCP decorators so they stay easy to unit-test.
In `main.py`, the MCP app must be mounted **last** and FastAPI must use `mcp_app.lifespan`, or MCP requests fail.

## Database

Postgres on [Neon](https://neon.com), accessed with `psycopg` (v3). Only `mcp-service` reads and writes
data at runtime; `db-migration` only changes the schema.

- `DATABASE_URL` lives in `.env.local` in the repo root (git-ignored), written by `neon link`.
  A real `DATABASE_URL` environment variable takes priority.
- Open connections with `with get_connection() as conn:` so they always close.
- Always pass values as query parameters (`conn.execute("... where id = %s", (id,))`), never f-strings.

### Schema changes (changesets)

Every schema change is a new SQL file in `db-migration/migrations/`, named with the next number: `002_add_issues.sql`.

- Applied files are recorded in `public.schema_migrations` with a checksum. **Never edit a file that has
  been applied**: the runner refuses it. Change the schema with a new file instead.
- Try a changeset on a Neon branch first, then run it on the main branch.
- DB tests run only when `TEST_DATABASE_URL` points at a throwaway Postgres; they drop the `nyc_today` schema.

### NYC Today tables (schema `nyc_today`)

- `runs`: one row per agent run (researcher, Vera check or Boss), with model and token usage.
- `items`: one row per item a researcher found, linked to its run by `run_id`.
  Absent optional values are `NULL`, never `''`; the constraints reject anything else.

## Conventions

- Each module starts with a short docstring explaining its purpose; comments are brief and explain *why*.
- When adding a dependency, add it to that service's `requirements.txt` only.

## Don'ts

- Never commit `.env` / `.env.*` files (except `.env.example`) or secrets.
- Don't commit `.neon` or `.venv/`.
- Don't import one service's code from another.
