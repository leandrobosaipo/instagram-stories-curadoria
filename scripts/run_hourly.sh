#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/Users/leandrobosaipo/.openclaw/workspace/projects/instagram-stories-curadoria"
ENV_FILE="$BASE_DIR/.env"
LOG_FILE="$BASE_DIR/logs/fetch.log"

mkdir -p "$BASE_DIR/logs"

cd "$BASE_DIR"
source "$BASE_DIR/.venv/bin/activate"
python "$BASE_DIR/scripts/fetch_stories_images.py" --env "$ENV_FILE" >> "$LOG_FILE" 2>&1
