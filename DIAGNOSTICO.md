# Diagnóstico técnico — coleta de stories privados (atualizado)

Data: 2026-03-11

## Skills buscadas/instaladas

- `gram` (ClawHub)
- `instagram-saver` (ClawHub)
- referência adicional já instalada: `instagram-scraper`

## Diagnóstico consolidado

1. Instaloader ficou instável para stories privados nesta conta (400 invalid request em GraphQL).
2. Houve sinais de limitação temporária de sessão (401 / "Please wait a few minutes").
3. Fluxos de login programático (instagrapi) caíram em challenge.
4. O caminho mais estável foi **cookies web + yt-dlp**.

## Refatoração aplicada

- Coletor reescrito para usar `yt-dlp` com `--cookies`.
- Filtro estrito de mídia:
  - `--match-filter "ext = 'jpg' | ext = 'jpeg' | ext = 'png' | ext = 'webp'"`
  - Resultado: baixa apenas imagens.
- Retry/backoff:
  - até 3 tentativas, com espera exponencial + jitter.
- Throttling:
  - `--sleep-requests 2`, `--min-sleep-interval 2`, `--max-sleep-interval 5`.
- Deduplicação:
  - estado em `data/state.json`.

## Teste executado

- Consulta da story list autenticada retornou **21 entradas**.
- Tipos detectados: **0 imagens / 21 vídeos**.
- Execução do coletor (modo imagem-only): **0 novas imagens baixadas** (esperado para o momento atual).

## Status do agendamento

- LaunchAgent ativo: `com.leandro.instagram-stories-curadoria`
- Intervalo: 3600s (1 hora)

## Boas práticas para reduzir risco de bloqueio

- Não rodar múltiplas instâncias em paralelo.
- Evitar refresh manual intenso durante a janela do job.
- Manter 1h+ entre coletas para stories privados.
- Pausar 6–24h se surgir `Please wait a few minutes`.
- Preferir sessão/cookie estável no mesmo dispositivo/IP.
