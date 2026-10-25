"""Load offices and agents from the markdown files in agents/<office>/.

Each office folder has one office.md (the orchestration) and one <agent>.md per agent.
Every file starts with YAML frontmatter between two `---` lines, then the prompt text.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
# Office and agent names come from URLs, so only allow simple names (no paths).
NAME = re.compile(r"^[a-z0-9_]+$")


@dataclass
class Doc:
    """One markdown file: its frontmatter and its prompt text."""

    meta: dict
    body: str


@dataclass
class Office:
    name: str
    meta: dict
    body: str
    agents: dict[str, Doc] = field(default_factory=dict)


def parse(path: Path) -> Doc:
    """Split a markdown file into frontmatter and body."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name}: must start with a --- frontmatter block")
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        raise ValueError(f"{path.name}: frontmatter is not closed with ---")
    return Doc(meta=yaml.safe_load(head) or {}, body=body.strip("\n"))


def list_offices(root: Path = AGENTS_DIR) -> list[str]:
    """Names of every office folder that has an office.md."""
    return sorted(p.parent.name for p in root.glob("*/office.md"))


def load_office(name: str, root: Path = AGENTS_DIR) -> Office:
    """Load an office and all its agents. Raises KeyError if it doesn't exist."""
    folder = root / name
    if not NAME.match(name) or not (folder / "office.md").is_file():
        raise KeyError(name)
    office = parse(folder / "office.md")
    agents = {p.stem: parse(p) for p in sorted(folder.glob("*.md")) if p.stem != "office"}
    for stem, doc in agents.items():
        if doc.meta.get("id") != stem:
            raise ValueError(f"{name}/{stem}.md: frontmatter id must be '{stem}'")
    return Office(name=name, meta=office.meta, body=office.body, agents=agents)


def build_prompt(office: Office) -> str:
    """The full scheduled-task prompt: office.md, then each agent in prompt_order.

    Agents missing from prompt_order are added at the end, so a new agent file is never left out.
    """
    order = list(office.meta.get("prompt_order") or [])
    unknown = [a for a in order if a not in office.agents]
    if unknown:
        raise ValueError(f"{office.name}: prompt_order names missing agents: {', '.join(unknown)}")
    order += [a for a in office.agents if a not in order]
    parts = [office.body] + [office.agents[a].body for a in order]
    return "\n\n".join(parts) + "\n"
