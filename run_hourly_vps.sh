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

# carrega variáveis do .env.vps (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)
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

send_tg() {
  local text="$1"
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" \
      -d "text=${text}" \
      -d "disable_notification=true" > /dev/null || true
  fi
}

if [ ! -f "$BASE/data/instagram-cookies.txt" ]; then
  echo "[$TS] skip: cookie ausente ($BASE/data/instagram-cookies.txt)" >> "$LOG"
  send_tg "⚠️ *Curadoria VPS*\n🕒 Hora (Cuiabá): $(fmt_cuiaba_now)\n⏭️ Sincronização não executada\nMotivo: cookie ausente em /app/data/instagram-cookies.txt"
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
    echo "[$TS] skip: cooldown ativo por 429 (${REM}s restantes)" >> "$LOG"

    send_tg "🚫 *Curadoria VPS — em BAN 429*\n🕒 Hora (Cuiabá): $(fmt_cuiaba_now)\n📌 Status: sincronização executada, mas *SKIP* por rate limit\n📅 Em ban desde: $(fmt_cuiaba_epoch "$BAN_SINCE")\n✅ Saída prevista do ban: $(fmt_cuiaba_epoch "$UNTIL")\n⏳ Restante: ${REM}s"
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

  send_tg "🚫 *Curadoria VPS — BAN 429 detectado*\n🕒 Hora (Cuiabá): $(fmt_cuiaba_now)\n📌 A sincronização rodou, mas bateu limite da Instagram\n📅 Ban começou: $(fmt_cuiaba_epoch "$NOW_EPOCH")\n✅ Saída prevista: $(fmt_cuiaba_epoch "$UNTIL")\n🔁 Próximas rodadas por hora ficarão em SKIP até liberar"
  rm -f "$TMP"
  exit $RC
fi

# resumo normal (sem 429)
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
  send_tg "✅ *Curadoria VPS — sincronização concluída*\n🕒 Hora (Cuiabá): $(fmt_cuiaba_now)\n📦 Novos memes enviados nesta rodada: ${SENT_NOW}\n📌 Status: sem ban 429"
else
  send_tg "⚠️ *Curadoria VPS — erro na sincronização*\n🕒 Hora (Cuiabá): $(fmt_cuiaba_now)\n📌 Status: execução com erro (sem 429)\n🧾 Verificar log: /opt/instagram-stories-curadoria/logs/vps-hourly.log"
fi

rm -f "$TMP"
exit $RC
