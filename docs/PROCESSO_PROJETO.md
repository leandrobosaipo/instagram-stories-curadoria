# Processo e Arquitetura do Projeto

## Fluxo
1. Coleta stories via endpoint `reels_media`
2. Salva imagens em `data/reels-media/<perfil>/<dia>/`
3. OCR em cada imagem (Tesseract)
4. Classificação por regras (`meme`, `noticia-propaganda`, `revisar`)
5. Envia no Telegram apenas `meme`
6. Deduplica envio por `telegram-sent-state.json`

## Deduplicação
- Coleta: `data/reels-media-state.json` (`seen_story_ids`)
- Envio: `data/curadoria/telegram-sent-state.json` (`sent`)

## Regras
Arquivo: `scripts/curadoria/rules.json`
- `priority` maior executa antes
- `order` desempata
- `set_label` força resultado
- `add_scores` soma pontos

## Execução local
```bash
source .venv/bin/activate
python scripts/curadoria/run_editorial_pipeline.py
```

## Execução Docker/VPS
```bash
docker build -t instagram-stories-curadoria .
docker run --rm --env-file .env.vps -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs instagram-stories-curadoria
```
