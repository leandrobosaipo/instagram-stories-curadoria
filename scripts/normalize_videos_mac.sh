#!/usr/bin/env bash
set -euo pipefail

BASE="/Users/leandrobosaipo/.openclaw/workspace/projects/instagram-stories-curadoria"

transcode_dir() {
  local SRC_DIR="$1"
  local OUT_DIR="$2"
  mkdir -p "$OUT_DIR"

  find "$SRC_DIR" -type f -name "*.mp4" | while read -r f; do
    local rel out
    rel="${f#$SRC_DIR/}"
    out="$OUT_DIR/$rel"
    mkdir -p "$(dirname "$out")"

    # pula se já existir
    if [[ -f "$out" ]]; then
      continue
    fi

    ffmpeg -y -i "$f" \
      -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p \
      -c:a aac -b:a 128k \
      -movflags +faststart \
      "$out" >/dev/null 2>&1
    echo "OK $out"
  done
}

transcode_dir "$BASE/data/manual-check" "$BASE/data/manual-check-mac"
transcode_dir "$BASE/data/stories" "$BASE/data/stories-mac"

echo "Concluído."