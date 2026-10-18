# NYC newsletter office

A small team of Claude agents that builds **NYC Today**, a daily newsletter about what's on in New York City. Each section of the newsletter gets its own researcher, and a fact-checker re-checks everything before it's used.

The office runs on Claude: a live page (an Artifact) shows the agents at their desks, and Claude scheduled tasks do the actual research.

## The team

| Agent | Job |
|---|---|
| **Rio** | Happy Hours: finds happy hours running that day and confirms each one on the venue's own website |
| **Fern** | Free Events: finds free, in-person events that day and confirms each one on the organizer's own page |
| **Vera** | Fact-check: re-opens every source Rio and Fern used and marks each item **Checked**, **Fixed** (with the correction) or **Dropped** (with the reason) |

Saved desks: Food, Music and Paid Events researchers, then an editor and a writer.

## How it fits together

```
office/index.html        the office page: pixel office, Run buttons, lists, Vera's verdicts, run history
prompts/office-run.md    scheduled task that runs a researcher, then Vera's check of that list
prompts/daily-trial.md   scheduled task that starts Rio and Fern each morning for a one-week trial
```

1. **Run whole team** on the page (or the daily trial task) starts the **office run** task with `STAGE: all | DATE: 2026-10-18 | MODEL: opus`. It runs the team in sequence in one session: Rio, Vera checks Rio, Fern, Vera checks Fern. A single researcher can also be run on its own (`STAGE: research | AGENT: rio | ...`).
2. Each researcher is spawned as a subagent and saves its list to the page's database, then **Vera** is spawned to check it. The page's step tracker shows which of the four steps is running.
3. The page updates live: each item shows Vera's verdict, and **Copy as newsletter lines** leaves out anything she dropped and uses her corrections.
4. The researcher's original list is never edited, so you can always see what Vera caught.

## Rules every agent follows

- Only sources from the venue or organizer count. List articles and roundups are used for leads, never as proof.
- Fewer confirmed items beat more unconfirmed ones. Nothing is padded or guessed.
- Everything is paraphrased; no copied listing text.

## Setting it up yourself

The IDs in this repo are placeholders. To run it:

1. Publish `office/index.html` as a Claude Artifact with the `db` capability and the Claude Code Remote connector (for starting runs).
2. Create a scheduled task from `prompts/office-run.md`, replacing `YOUR_ARTIFACT_URL` with your artifact's link.
3. Put that task's ID in `office/index.html` (`TRIGGER_ID`), then republish the page.
4. Optional: create the daily trial task from `prompts/daily-trial.md`, filling in both task IDs and the artifact link.
