#!/usr/bin/env bash
# agent/install_service.sh
# Quick helper to run syslog-listener in background. Edit paths as needed.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"
  pip install requests
else
  source "$VENV_DIR/bin/activate"
fi

# Example invocation: change backend and key
python "$SCRIPT_DIR/syslog-listener.py" --bind 0.0.0.0 --port 5514 --backend http://127.0.0.1:8000/event --api-key "YOUR_KEY"