#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/Users/leandrobosaipo/.openclaw/workspace/projects/instagram-stories-curadoria"
LOG_FILE="$BASE_DIR/logs/fetch-posts-images.log"

mkdir -p "$BASE_DIR/logs"
cd "$BASE_DIR"
source "$BASE_DIR/.venv/bin/activate"
python "$BASE_DIR/scripts/fetch_profile_post_images.py" --env "$BASE_DIR/.env.posts" >> "$LOG_FILE" 2>&1
