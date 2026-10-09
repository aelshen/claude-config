#!/usr/bin/env bash
# One-time setup: a venv with Playwright (Chromium) and Pillow inside the skill folder. ffmpeg comes from Homebrew.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v ffmpeg >/dev/null || { echo "ffmpeg missing: brew install ffmpeg"; exit 1; }
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m playwright install chromium
echo "ready: $(pwd)/.venv/bin/python"
