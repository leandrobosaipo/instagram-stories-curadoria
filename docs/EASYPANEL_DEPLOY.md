# Deploy no EasyPanel — GitHub Token

## ✅ Pré-requisitos

- [x] Token GitHub criado e salvo no EasyPanel
- [x] Repo: https://github.com/leandrobosaipo/instagram-stories-curadoria

---

## 🚀 Passo a Passo

### 1) Criar App no EasyPanel

- **Tipo:** App → Git Repository
- **Repository:** `leandrobosaipo/instagram-stories-curadoria`
- **Branch:** `main`
- **Build:** Dockerfile (automático)

---

### 2) Variáveis de Ambiente

Copiar do `.env.vps.example`:

```env
# Instagram fonte
TARGET_PROFILE=perrenguematogrosso
COOKIES_FILE=/app/data/instagram-cookies.txt
OUTPUT_DIR=/app/data/reels-media
STATE_FILE=/app/data/reels-media-state.json
IG_APP_ID=936619743392459

# Telegram destino
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui
TELEGRAM_SILENT=false
TELEGRAM_MAX_PER_RUN=50

# Curadoria
RULES_FILE=/app/scripts/curadoria/rules.json
TESSERACT_BIN=/usr/bin/tesseract

# Estado de envio
SENT_STATE_FILE=/app/data/curadoria/telegram-sent-state.json
```

---

### 3) Volumes Persistentes

Montar para não perder dados entre restarts:

| Container Path | Descrição |
|----------------|-----------|
| `/app/data` | Cookies, state, memes baixados |
| `/app/logs` | Logs de execução |

---

### 4) Cookie do Instagram

**Opção A:** Copiar arquivo existente do Mac

```bash
# Local
scp data/instagram-cookies.txt user@vps:/tmp/

# Na VPS
docker cp /tmp/instagram-cookies.txt NOME_CONTAINER:/app/data/
```

**Opção B:** Extrair novo cookie

1. Logar no Instagram no navegador da VPS
2. Usar extensão "EditThisCookie" ou similar
3. Exportar em formato Netscape
4. Salvar em `/app/data/instagram-cookies.txt`

---

### 5) Primeira Execução (INITIAL RUN)

Rodar manualmente com flag `--initial-run` para enviar todos os memes acumulados:

```bash
# No EasyPanel → Execute Command
python scripts/curadoria/run_editorial_pipeline.py --initial-run --skip-fetch
```

**Flags:**
- `--initial-run`: Processa TODOS os dias, ignora state anterior
- `--skip-fetch`: Pula coleta (usa dados já existentes no volume)

> ⚠️ Se não tiver dados no volume, remova `--skip-fetch` para coletar stories primeiro.

---

### 6) Configurar Cron (1h)

- **Schedule:** `0 * * * *`
- **Command:** `python scripts/curadoria/run_editorial_pipeline.py`

---

### 7) Testar

1. Executar job manualmente
2. Verificar logs
3. Confirmar recebimento no Telegram

---

## 🔧 Troubleshooting

| Erro | Solução |
|------|---------|
| `403 Telegram` | chat_id errado ou não deu `/start` no bot |
| `tesseract not found` | Ajustar `TESSERACT_BIN=/usr/bin/tesseract` |
| `Permission denied` | Verificar se volume está montado corretamente |
| `No module named 'requests'` | Build falhou — verificar Dockerfile |

---

## 📊 Flags do Pipeline

| Flag | Descrição |
|------|-----------|
| `--initial-run` | Primeira execução: envia TODOS os memes |
| `--skip-fetch` | Pula coleta (usa dados existentes) |
| `--dry-run` | Não envia para Telegram, só mostra |

---

## 🔄 Atualizar Código

Após mudanças no repo:

```bash
# Local
git add . && git commit -m "update" && git push

# EasyPanel
# → Redeploy (automático se webhook configurado)
```
