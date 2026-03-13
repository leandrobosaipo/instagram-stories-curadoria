# Instagram Stories Curadoria (somente imagens)

Projeto para buscar stories de perfil privado com **cookie de sessão web** e salvar **apenas imagens** (sem vídeos), com deduplicação e execução de hora em hora.

## Requisitos

- Python 3.12+
- `yt-dlp`

## Setup

```bash
cd /Users/leandrobosaipo/.openclaw/workspace/projects/instagram-stories-curadoria
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edite .env
```

## Cookie file (Netscape)

Crie `data/instagram-cookies.txt` com os cookies da sessão logada no Instagram.

## Execução manual

```bash
source .venv/bin/activate
python scripts/fetch_stories_images.py --env .env
```

## Agendamento (macOS LaunchAgent - 1h)

```bash
mkdir -p ~/Library/LaunchAgents
cp launchd/com.leandro.instagram-stories-curadoria.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.leandro.instagram-stories-curadoria.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.leandro.instagram-stories-curadoria.plist
launchctl start com.leandro.instagram-stories-curadoria
```

## Boas práticas anti-bloqueio (importante)

- Usar **uma única instância** do job (nada em paralelo).
- Evitar uso intenso da conta em app/browser no mesmo minuto do job.
- Intervalo de 1h está OK para stories; evitar rodar a cada poucos minutos.
- Script já aplica `sleep` entre requests e retry com backoff.
- Se aparecer `Please wait a few minutes`, pausar por 6–24h.
- Manter sessão/cookies atualizados e evitar troca brusca de IP/dispositivo.

## Saída

- Imagens: `data/stories/<perfil>/YYYY-MM-DD/`
- Estado: `data/state.json`
- Logs: `logs/fetch.log`

## Curadoria (OCR + Regras)

Arquivos centralizados em `scripts/curadoria/`:

- `scripts/curadoria/rules.json` (regras editáveis: prioridade/ordem/peso/override)
- `scripts/curadoria/rule_engine.py` (classe de aplicação das regras)
- `scripts/curadoria/README.md` (guia de manutenção)

Execução:

```bash
source .venv/bin/activate
python scripts/classify_story_images.py --input data/reels-media/<perfil>/<YYYY-MM-DD> --output data/curadoria/<YYYY-MM-DD>
```
