#!/usr/bin/env bash
set -euo pipefail

BASE="/Users/leandrobosaipo/.openclaw/workspace/projects/instagram-stories-curadoria"
COOKIES="$BASE/data/instagram-cookies.txt"
OUT="$BASE/data/stories-thumbnails/perrenguematogrosso/$(date +%F)"
URL="https://www.instagram.com/stories/perrenguematogrosso/"

mkdir -p "$OUT"

yt-dlp \
  --cookies "$COOKIES" \
  --skip-download \
  --write-thumbnail \
  --convert-thumbnails jpg \
  --sleep-requests 2 \
  --min-sleep-interval 2 \
  --max-sleep-interval 5 \
  --retries 3 \
  --fragment-retries 3 \
  --socket-timeout 25 \
  --no-overwrites \
  -o "$OUT/%(id)s.%(ext)s" \
  "$URL"

echo "Thumbs em: $OUT"