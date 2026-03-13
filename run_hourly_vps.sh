#!/usr/bin/env bash
set -euo pipefail

BASE=/opt/instagram-stories-curadoria
LOG="$BASE/logs/vps-hourly.log"
COOLDOWN_FILE="$BASE/data/.ig_429_cooldown_until"
BAN_SINCE_FILE="$BASE/data/.ig_429_since"
ENV_FILE="$BASE/.env.vps"

mkdir -p "$BASE/logs" "$BASE/data"
TS="$(date '+%Y-%m-%d %H:%M:%S %Z')"
NOW_EPOCH=$(date +%s)

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

fmt_cuiaba_epoch() {
  local epoch="$1"
  TZ=America/Cuiaba date -d "@$epoch" "+%d/%m/%Y %H:%M:%S (%Z)"
}

fmt_cuiaba_now() {
  TZ=America/Cuiaba date "+%d/%m/%Y %H:%M:%S (%Z)"
}

humanize_seconds() {
  local s="$1"
  local h=$((s/3600))
  local m=$(((s%3600)/60))
  if [ "$h" -gt 0 ] && [ "$m" -gt 0 ]; then
    echo "${h}h ${m}min"
  elif [ "$h" -gt 0 ]; then
    echo "${h}h"
  elif [ "$m" -gt 0 ]; then
    echo "${m}min"
  else
    echo "< 1min"
  fi
}

send_tg() {
  local text="$1"
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${text}" \
      --data-urlencode "parse_mode=HTML" \
      --data-urlencode "disable_notification=true" \
      --data-urlencode "disable_web_page_preview=true" > /dev/null || true
  fi
}

notify_template() {
  local icon="$1"
  local title="$2"
  local status="$3"
  local details="$4"

  send_tg "${icon} <b>${title}</b>
━━━━━━━━━━━━━━━━━━
🕒 <b>Hora (Cuiabá):</b> $(fmt_cuiaba_now)
📌 <b>Status:</b> ${status}
${details}"
}

if [ ! -f "$BASE/data/instagram-cookies.txt" ]; then
  echo "[$TS] skip: cookie ausente ($BASE/data/instagram-cookies.txt)" >> "$LOG"
  notify_template "⚠️" "Curadoria VPS" "sincronização não executada" "📌 <b>Motivo:</b> cookie ausente em /app/data/instagram-cookies.txt"
  exit 0
fi

if [ -f "$COOLDOWN_FILE" ]; then
  UNTIL=$(cat "$COOLDOWN_FILE" 2>/dev/null || echo 0)
  if [ "$UNTIL" -gt "$NOW_EPOCH" ] 2>/dev/null; then
    if [ -f "$BAN_SINCE_FILE" ]; then
      BAN_SINCE=$(cat "$BAN_SINCE_FILE" 2>/dev/null || echo $((UNTIL-21600)))
    else
      BAN_SINCE=$((UNTIL-21600))
    fi

    REM=$((UNTIL-NOW_EPOCH))
    REM_HUMAN=$(humanize_seconds "$REM")
    echo "[$TS] skip: cooldown ativo por 429 (${REM}s restantes)" >> "$LOG"

    notify_template "🚫" "Curadoria VPS — BAN 429 ativo" "sincronização em SKIP por rate limit" "📅 <b>Em ban desde:</b> $(fmt_cuiaba_epoch "$BAN_SINCE")
✅ <b>Saída prevista:</b> $(fmt_cuiaba_epoch "$UNTIL")
⏳ <b>Tempo restante:</b> ${REM_HUMAN}"
    exit 0
  else
    rm -f "$COOLDOWN_FILE" "$BAN_SINCE_FILE"
  fi
fi

TMP=$(mktemp)
set +e
docker run --rm \
  -e ENV_FILE=/app/.env.vps \
  -v "$BASE/.env.vps:/app/.env.vps:ro" \
  -v "$BASE/data:/app/data" \
  -v "$BASE/logs:/app/logs" \
  ig-curadoria:vps \
  python scripts/curadoria/run_editorial_pipeline.py > "$TMP" 2>&1
RC=$?
set -e
cat "$TMP" >> "$LOG"

if grep -q "429\|Too Many Requests" "$TMP"; then
  UNTIL=$((NOW_EPOCH + 21600))
  echo "$UNTIL" > "$COOLDOWN_FILE"
  echo "$NOW_EPOCH" > "$BAN_SINCE_FILE"
  echo "[$TS] 429 detectado -> cooldown de 6h ativado" >> "$LOG"

  notify_template "🚫" "Curadoria VPS — BAN 429 detectado" "sincronização rodou, mas bateu limite da Instagram" "📅 <b>Ban começou:</b> $(fmt_cuiaba_epoch "$NOW_EPOCH")
✅ <b>Saída prevista:</b> $(fmt_cuiaba_epoch "$UNTIL")
🔁 <b>Próximas rodadas:</b> SKIP horário até liberar"
  rm -f "$TMP"
  exit $RC
fi

SENT_NOW=$(python3 - <<'PY'
import json
from pathlib import Path
p=Path('/opt/instagram-stories-curadoria/data/curadoria/telegram-sent-state.json')
if p.exists():
    d=json.loads(p.read_text())
    print(d.get('last_sent_count', 0))
else:
    print(0)
PY
)

if [ "$RC" -eq 0 ]; then
  notify_template "✅" "Curadoria VPS — sincronização concluída" "sem ban 429" "📦 <b>Memes enviados nesta rodada:</b> ${SENT_NOW}"
else
  notify_template "⚠️" "Curadoria VPS — erro na sincronização" "execução com erro (sem 429)" "🧾 <b>Log:</b> /opt/instagram-stories-curadoria/logs/vps-hourly.log"
fi

rm -f "$TMP"
exit $RC
