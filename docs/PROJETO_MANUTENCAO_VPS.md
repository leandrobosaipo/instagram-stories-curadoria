# Instagram Stories Curadoria — Operação, Manutenção e Evolução (VPS)

## 1) O que o projeto faz

Pipeline automatizado para:
1. Coletar stories do perfil alvo (`reels_media`)
2. Extrair texto via OCR (Tesseract)
3. Classificar com regras (`meme`, `noticia-propaganda`, `revisar`)
4. Enviar no Telegram somente o que for `meme`
5. Evitar duplicados por arquivo de estado

---

## 2) Como funciona (arquitetura)

### Entrada
- Perfil alvo: `TARGET_PROFILE`
- Cookies Instagram: `data/instagram-cookies.txt`

### Processamento
- Coleta: `scripts/fetch_stories_reels_media.py`
- Classificação: `scripts/classify_story_images.py`
- Regras: `scripts/curadoria/rules.json`
- Orquestração: `scripts/curadoria/run_editorial_pipeline.py`

### Saída
- Curadoria por dia: `data/curadoria/YYYY-MM-DD/`
- Estado de envio Telegram: `data/curadoria/telegram-sent-state.json`
- Estado de coleta: `data/reels-media-state.json`

---

## 3) Estado atual (13/03/2026)

- Deploy validado na VPS `147.93.134.213`
- Imagem Docker: `ig-curadoria:vps`
- Primeira execução VPS concluída com sucesso e envio no Telegram
- Agendamento horário criado via `crontab`
- **Local desativado** (LaunchAgent e processos locais encerrados)

### Importante
- Ainda falta cookie na VPS para coleta contínua de novos stories:
  - caminho esperado: `/opt/instagram-stories-curadoria/data/instagram-cookies.txt`

---

## 4) Requisitos para rodar na VPS

## Infra
- Docker instalado
- Acesso root ou sudo
- Conectividade com Telegram API

## Variáveis obrigatórias (`.env.vps`)
- `TARGET_PROFILE`
- `COOKIES_FILE`
- `OUTPUT_DIR`
- `STATE_FILE`
- `IG_APP_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `RULES_FILE`
- `SENT_STATE_FILE`
- `TESSERACT_BIN`

## Volumes
- `/opt/instagram-stories-curadoria/data:/app/data`
- `/opt/instagram-stories-curadoria/logs:/app/logs`

---

## 5) Operação (comandos principais)

## Build imagem
```bash
cd /opt/instagram-stories-curadoria
docker build -t ig-curadoria:vps .
```

## Primeira execução (forçar acervo existente)
```bash
docker run --rm \
  -e ENV_FILE=/app/.env.vps \
  -v /opt/instagram-stories-curadoria/.env.vps:/app/.env.vps:ro \
  -v /opt/instagram-stories-curadoria/data:/app/data \
  -v /opt/instagram-stories-curadoria/logs:/app/logs \
  ig-curadoria:vps \
  python scripts/curadoria/run_editorial_pipeline.py --initial-run --skip-fetch
```

## Execução normal
```bash
docker run --rm \
  -e ENV_FILE=/app/.env.vps \
  -v /opt/instagram-stories-curadoria/.env.vps:/app/.env.vps:ro \
  -v /opt/instagram-stories-curadoria/data:/app/data \
  -v /opt/instagram-stories-curadoria/logs:/app/logs \
  ig-curadoria:vps \
  python scripts/curadoria/run_editorial_pipeline.py
```

## Agendamento (já criado)
- Script: `/opt/instagram-stories-curadoria/run_hourly_vps.sh`
- Cron: `0 * * * * /opt/instagram-stories-curadoria/run_hourly_vps.sh`
- Log: `/opt/instagram-stories-curadoria/logs/vps-hourly.log`

---

## 6) Troubleshooting rápido

## `TARGET_PROFILE não definido`
- Rode com `-e ENV_FILE=/app/.env.vps`
- Monte o arquivo env: `-v /opt/.../.env.vps:/app/.env.vps:ro`

## `Permission denied` em `/app/data`
- Ajustar ownership:
```bash
chown -R 1000:1000 /opt/instagram-stories-curadoria/data /opt/instagram-stories-curadoria/logs
```

## Sem novos memes
- Stories podem ter expirado
- Cookie pode estar inválido
- Verificar `reels-media-state.json` e logs

---

## 7) Como evoluir o projeto

1. **Adicionar mais fontes (perfis):**
   - Executar uma instância por perfil (envs separados)
   - Ex.: `TARGET_PROFILE=perfil_x` com `SENT_STATE_FILE` dedicado

2. **Escalar classificação:**
   - Ajustar `rules.json` com pesos por contexto
   - Criar regras por perfil/fonte

3. **Melhorar confiabilidade:**
   - Alertas de falha no Telegram/Discord
   - Healthcheck + retries com backoff

4. **Governança de conteúdo:**
   - Blacklist de termos/marcas
   - Limite diário de envio por categoria

---

## 8) Skills recomendadas (OpenClaw) para reinstalar/manter

Para manutenção operacional e expansão:
- `github` → versionamento, PRs, releases
- `vps` → operação e deploy em servidor
- `Sysadmin` → troubleshooting Linux/processos/cron
- `docker-essentials` → build, imagens, containers
- `ops-hygiene` → rotina de manutenção e segurança
- `healthcheck` → auditoria de saúde e hardening

Para expansão de fontes e automações:
- `blogwatcher` (se adicionar RSS/fontes externas)
- `gog` (se integrar com planilhas/Google)
- `wacli` (se houver distribuição paralela via WhatsApp)

---

## 9) Checklist de retomada (quando abrir nova sessão)

1. Confirmar que local continua desativado
2. Verificar cron na VPS
3. Verificar presença/validade do cookie na VPS
4. Rodar execução manual de teste
5. Conferir envio Telegram e estado (`telegram-sent-state.json`)
6. Registrar mudanças no `MEMORY.md` e nesta documentação
