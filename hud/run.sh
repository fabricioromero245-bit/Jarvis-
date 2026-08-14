#!/usr/bin/env bash
# One command to open the HUD. Bootstraps a venv on first run, then
# just launches — safe to run every time.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

exec python3 hud.py "$@"
