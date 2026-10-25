#!/usr/bin/env bash
# Set up the environment and apply the SQL changesets in migrations/.
#   ./migrate.sh            -> apply pending changesets
#   ./migrate.sh --status   -> show applied, pending and edited changesets
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"

# Windows venvs use Scripts/, macOS/Linux use bin/
if [ -d "$VENV/Scripts" ] || [[ "$(uname -s)" == MINGW* || "$(uname -s)" == MSYS* ]]; then
  BIN="$VENV/Scripts"
else
  BIN="$VENV/bin"
fi

# 1. Create the virtual environment if it doesn't exist
if [ ! -d "$VENV" ]; then
  echo "Creating virtual environment in $VENV..."
  python -m venv "$VENV"
fi

# 2. Install / update requirements
if ! "$BIN/python" -m pip --version >/dev/null 2>&1; then
  "$BIN/python" -m ensurepip --upgrade >/dev/null
fi
"$BIN/python" -m pip install --quiet --upgrade pip
"$BIN/python" -m pip install --quiet -r requirements.txt

# 3. Run the migrations
exec "$BIN/python" migrate.py "$@"
