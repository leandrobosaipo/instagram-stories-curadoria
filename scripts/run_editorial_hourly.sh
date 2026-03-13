#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/Users/leandrobosaipo/.openclaw/workspace/projects/instagram-stories-curadoria"
LOG_FILE="$BASE_DIR/logs/editorial-hourly.log"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export TESSERACT_BIN="${TESSERACT_BIN:-/opt/homebrew/bin/tesseract}"

mkdir -p "$BASE_DIR/logs"
cd "$BASE_DIR"
source "$BASE_DIR/.venv/bin/activate"
python "$BASE_DIR/scripts/curadoria/run_editorial_pipeline.py" >> "$LOG_FILE" 2>&1
