"""Apply the SQL changesets in migrations/ to the database, in order, once each.

Each file `NNN_short_name.sql` is one changeset. Applied changesets are recorded in
public.schema_migrations with a checksum, so a file that already ran is never re-run,
and editing one is refused: fix the schema with a new changeset instead.

    ./migrate.sh            # apply pending changesets
    ./migrate.sh --status   # show applied and pending
"""

import hashlib
import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

# DATABASE_URL comes from .env.local in the repo root (written by `neon link`).
# A real environment variable wins.
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
FILENAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
# Any fixed number works; it just stops two migrate runs from overlapping.
LOCK_ID = 718_224_001


def get_connection() -> psycopg.Connection:
    """Open a connection to DATABASE_URL. Use it in a `with` block so it closes."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Run `neon link` or add it to .env.local in the repo root.")
    return psycopg.connect(url)


def changesets(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """Return the changeset files in apply order. Rejects badly named or duplicate-numbered files."""
    files = sorted(p for p in directory.glob("*.sql"))
    seen: dict[str, str] = {}
    for p in files:
        m = FILENAME.match(p.name)
        if not m:
            raise ValueError(f"{p.name}: changesets must be named NNN_short_name.sql")
        if m.group(1) in seen:
            raise ValueError(f"{p.name} and {seen[m.group(1)]} share the number {m.group(1)}")
        seen[m.group(1)] = p.name
    return files


def checksum(path: Path) -> str:
    """SHA-256 of the file, ignoring line-ending differences between machines."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _applied(conn: psycopg.Connection) -> dict[str, str]:
    conn.execute(
        """
        create table if not exists public.schema_migrations (
            version    text primary key,
            checksum   text not null,
            applied_at timestamptz not null default now()
        )
        """
    )
    return dict(conn.execute("select version, checksum from public.schema_migrations").fetchall())


def migrate(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply every pending changeset, each in its own transaction. Returns the names applied."""
    files = changesets(directory)
    conn.execute("select pg_advisory_lock(%s)", (LOCK_ID,))
    try:
        with conn.transaction():
            applied = _applied(conn)
        for p in files:
            if p.name in applied and applied[p.name] != checksum(p):
                raise RuntimeError(f"{p.name} was edited after it was applied. Add a new changeset instead.")
        done = []
        for p in files:
            if p.name in applied:
                continue
            with conn.transaction():
                # No parameters, so psycopg sends the whole file as one multi-statement query.
                conn.execute(p.read_text())
                conn.execute(
                    "insert into public.schema_migrations (version, checksum) values (%s, %s)",
                    (p.name, checksum(p)),
                )
            done.append(p.name)
        return done
    finally:
        conn.execute("select pg_advisory_unlock(%s)", (LOCK_ID,))


def status(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[tuple[str, str]]:
    """List each changeset with its state: applied, pending, or edited."""
    with conn.transaction():
        applied = _applied(conn)
    rows = []
    for p in changesets(directory):
        if p.name not in applied:
            rows.append((p.name, "pending"))
        elif applied[p.name] != checksum(p):
            rows.append((p.name, "edited"))
        else:
            rows.append((p.name, "applied"))
    return rows


def main() -> None:
    with get_connection() as conn:
        conn.autocommit = True  # each changeset runs in its own explicit transaction
        if "--status" in sys.argv[1:]:
            for name, state in status(conn):
                print(f"{state:8} {name}")
            return
        done = migrate(conn)
        print("\n".join(f"applied  {n}" for n in done) or "Nothing to apply.")


if __name__ == "__main__":
    main()
