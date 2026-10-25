#!/usr/bin/env bash
# Set up the environment and run the MCP service. Press Ctrl+C to stop.
#   ./start.sh            -> runs on port 8000
#   PORT=9000 ./start.sh  -> runs on another port
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
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
echo "Installing requirements..."
"$BIN/python" -m pip install --quiet --upgrade pip
"$BIN/python" -m pip install --quiet -r requirements.txt

# 3. Run the server (auto-reloads when you save a file)
echo "Starting server on http://127.0.0.1:$PORT"
echo "  Docs: http://127.0.0.1:$PORT/docs   MCP: http://127.0.0.1:$PORT/mcp"
echo "  Press Ctrl+C to stop."
exec "$BIN/python" -m uvicorn main:app --host 127.0.0.1 --port "$PORT" --reload
