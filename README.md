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

## How it fits together

```
office/index.html        the office page: pixel office, Run buttons, lists, Vera's verdicts, the issue, run history
prompts/office-run.md    scheduled task that runs the researchers, Vera's checks and the Boss
prompts/daily-trial.md   scheduled task that started the team each morning for a one-week trial (turned off)
```

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

Any item missing a required field is **dropped** by Vera, never filled in. The matching Postgres tables (`nyc_today.runs` and `nyc_today.items`) live in the [my-mcp](https://github.com/RajeenKhadka/my-mcp) repo.

## Rules every agent follows

- Only sources from the venue or organizer count. List articles and roundups are used for leads, never as proof.
- Fewer confirmed items beat more unconfirmed ones. Nothing is padded or guessed.
- Everything is paraphrased; no copied listing text.

## Life in the office

Between runs the team has some personality. They grab coffee, visit each other's desks, high-five when someone finishes a list, and get pulled into the Boss's standups. After each review the Boss calls everyone in for a 1:1. A caterer restocks the food counter, and Mochi the bodega cat does as he pleases.

## Setting it up yourself

The IDs in this repo are placeholders. To run it:

1. Publish `office/index.html` as a Claude Artifact with the `db` capability and the Claude Code Remote connector (for starting runs).
2. Create a scheduled task from `prompts/office-run.md`, replacing `YOUR_ARTIFACT_URL` with your artifact's link.
3. Put that task's ID in `office/index.html` (`TRIGGER_ID`), then republish the page.
4. Optional: create the daily trial task from `prompts/daily-trial.md`, filling in both task IDs and the artifact link.
