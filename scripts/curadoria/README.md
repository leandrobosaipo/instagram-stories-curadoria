# Curadoria por Regras (OCR + Engine)

Esta pasta concentra tudo da classificação para manter o projeto organizado.

## Estrutura

- `rules.json` → regras editáveis (prioridade, ordem, score e override)
- `rule_engine.py` → classe `CuradoriaRules` que aplica as regras
- `../classify_story_images.py` → script CLI que roda OCR e usa a engine

## Como editar regras (iniciante)

Abra `rules.json` e ajuste apenas os campos abaixo:

- `enabled`: `true/false` (liga/desliga regra)
- `priority`: número inteiro (maior roda antes)
- `order`: desempate dentro da mesma prioridade (menor roda antes)
- `when_any`: se qualquer termo bater, a regra casa
- `when_all`: todos os termos precisam bater
- `when_not_any`: se algum termo aparecer, bloqueia a regra
- `when_regex`: regex para padrões (telefone, preço etc.)
- `add_scores`: soma pontos por classe
- `set_label`: força rótulo final
- `stop_on_match`: para processamento após essa regra

## Fluxo de decisão

1. OCR extrai texto da imagem
2. Texto é normalizado (minúsculo + sem acento)
3. Regras são processadas por `priority` e `order`
4. Regras podem:
   - somar score
   - forçar rótulo
5. Sem override, aplica limiares:
   - `noticia-propaganda` se score >= threshold
   - `meme` se score meme >= threshold e score notícia = 0
   - caso contrário `revisar`

## Executar

```bash
source .venv/bin/activate
python scripts/classify_story_images.py \
  --input data/reels-media/perrenguematogrosso/2026-03-11 \
  --output data/curadoria/2026-03-11
```

## Dica de manutenção

- Regra errada? deixe `enabled: false` antes de apagar.
- Primeiro ajuste termos em `when_any`, depois mexa em `priority`.
- Use `report.json` para ver quais regras bateram por arquivo.
