# NYC newsletter office

A small team of Claude agents that builds **NYC Today**, a daily newsletter about what's on in New York City. Each section of the newsletter gets its own researcher, a fact-checker re-checks everything, and a manager puts the checked lists together into the day's issue.

The office runs on Claude: a live page (an Artifact) shows the agents at their desks, and a Claude scheduled task does the actual research.

## The team

| Agent | Job |
|---|---|
| **Rio** | Happy Hours: happy hours running that day, confirmed on the venue's own website |
| **Fern** | Free Events: free, in-person events that day, confirmed on the organizer's own page |
| **Basil** | Food: food specials and food events, confirmed on the restaurant's or organizer's own page |
| **Juno** | Music: live shows (no arenas, at most 2 free), confirmed on the venue's or ticket page |
| **Vera** | Fact-check: re-opens every source and marks each item **Checked**, **Fixed** (with the correction) or **Dropped** (with the reason) |
| **The Boss** | Manager (always Sonnet): builds the issue from Vera-checked items only, picks 3 editor's picks, removes duplicates, then reviews each agent |

Saved desks: Paid Events, then an editor and a writer. Next door, the **Dev Office** (Ivy, a designer) will turn each issue into an email and a web page.

## Repo layout

Each folder is its own service you can start on its own.

```
mcp-service/      MCP server (FastMCP + FastAPI). Port 8000. The only service that talks to Postgres.
  app/            server.py (tools), db.py (Postgres connection), tools/
  main.py  requirements.txt  start.sh
agent-service/    Agent prompts, one markdown file per agent. Port 8001.
  agents/<office>/office.md     how the office runs (stages, database docs, stopping)
  agents/<office>/<agent>.md    one file per agent: rio, fern, basil, juno, vera, boss
  web/<office>/index.html       the office page (published as a Claude Artifact)
  app/  main.py  requirements.txt  start.sh
db-migration/     SQL changesets for Postgres. Runs once and exits.
  migrations/NNN_name.sql  migrate.py  migrate.sh
.env.example      copy to .env.local (shared by every service)
```

Start a service locally:

```bash
./mcp-service/start.sh        # http://127.0.0.1:8000  (MCP at /mcp, docs at /docs)
./agent-service/start.sh      # http://127.0.0.1:8001  (offices at /offices)
./db-migration/migrate.sh     # apply pending changesets (--status to just look)
```

Each script makes its own `.venv` and installs its `requirements.txt` the first time.

### Agent files

Every agent file starts with frontmatter, then its prompt:

```md
---
id: rio
name: Rio
role: researcher
section: Happy Hours
model: opus
---

=== BRIEF: rio ===
"You are Rio, the Happy Hours researcher ...
```

`GET /offices/nyc_today/prompt` stitches `office.md` and every agent (in `prompt_order`) into the full prompt for the **NYC Today office run** scheduled task. Edit an agent's file, then paste that output into the task. A new office is a new folder in `agents/` with its own `office.md`.

## How a run works

1. **Run whole team** on the page starts the **office run** task with `STAGE: all | DATE: <YYYY-MM-DD> | MODEL: opus`. All four researchers work at the same time, then Vera checks each list one at a time (Rio, Fern, Basil, Juno), then the Boss builds the issue and the team review. A single researcher can also be run on its own (`STAGE: research | AGENT: rio | ...`).
2. Each agent is spawned as a subagent and everything is saved to the page's database (collection `office`).
3. The page updates live: each item shows Vera's verdict, and **Copy as newsletter lines** leaves out anything she dropped and uses her corrections.
4. The researcher's original list is never edited, so you can always see what Vera caught.

## Item shape

Every researcher returns items in one identical shape, so code (no AI) can store them in a database and fill a reusable email template.

```json
{
  "name": "Mermaid Oyster Bar",
  "venue": "Mermaid Oyster Bar",
  "url": "https://www.themermaidnyc.com/mermaid-oyster-bar-menus/",
  "summary": "$2 oysters and clams by the half dozen, $8 draft beer, $10 wine",
  "neighborhood": "Greenwich Village",
  "borough": "Manhattan",
  "time": "4:30–6pm",
  "price": "$$",
  "address": "89 MacDougal St",
  "condition": null,
  "overview": "A seafood restaurant and oyster bar with a raw bar.",
  "confirmedOn": "venue happy hour menu page",
  "sourceDate": null
}
```

- **Required, never null or empty:** `name`, `venue`, `url`, `summary`, `neighborhood`, `borough`, `time`, `price`, `address`, `confirmedOn`.
- **Optional, a string or `null`:** `condition`, `overview`, `sourceDate`. Never `""` or `"not shown"`.
- `venue` is always present; for a happy hour or food special it is the bar or restaurant name.
- `address` is street only (no city, state or ZIP). `borough` is one of the five boroughs. `sourceDate` is `YYYY-MM-DD`.
- `summary` is under 15 words, `overview` under 30 words, `confirmedOn` under 80 characters.
- Price: Happy Hours and Food use tiers (`$`, `$$`, `$$$`, `Free`); Music and Free Events keep the price exactly as stated.
- `confirmedOn` and `sourceDate` are internal (for Vera and metrics), not shown to readers.

Any item missing a required field is **dropped** by Vera, never filled in. The matching Postgres tables (`nyc_today.runs` and `nyc_today.items`) are in `db-migration/migrations/`.

## Rules every agent follows

- Only sources from the venue or organizer count. List articles and roundups are used for leads, never as proof.
- Fewer confirmed items beat more unconfirmed ones. Nothing is padded or guessed.
- Everything is paraphrased; no copied listing text.

## Life in the office

Between runs the team has some personality. They grab coffee, visit each other's desks, high-five when someone finishes a list, and get pulled into the Boss's standups. After each review the Boss calls everyone in for a 1:1. A caterer restocks the food counter, and Mochi the bodega cat does as he pleases.

## Setting it up yourself

The IDs in this repo are placeholders. To run it:

1. Publish `agent-service/web/nyc_today/index.html` as a Claude Artifact with the `db` capability and the Claude Code Remote connector (for starting runs).
2. Start the agent service and create a scheduled task from `GET /offices/nyc_today/prompt`, replacing `YOUR_ARTIFACT_URL` with your artifact's link.
3. Put that task's ID in the page (`TRIGGER_ID`), then republish it.
