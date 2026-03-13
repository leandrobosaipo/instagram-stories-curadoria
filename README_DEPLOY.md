# Deploy no GitHub + EasyPanel (VPS)

## 1) Repositório

Repo atualizado:
```
https://github.com/leandrobosaipo/instagram-stories-curadoria
```

---

## 2) Clone no EasyPanel (3 opções)

### 🔑 Opção A: Personal Access Token (mais rápido)

1. Gere um PAT no GitHub: https://github.com/settings/tokens
   - Selecione escopo `repo`
   - Copie o token

2. No EasyPanel, use URL com token:
```
https://<SEU_TOKEN>@github.com/leandrobosaipo/instagram-stories-curadoria.git
```

**Alternativa:** Adicione o token como variável de ambiente `GITHUB_TOKEN` no EasyPanel e use:
```
https://${GITHUB_TOKEN}@github.com/leandrobosaipo/instagram-stories-curadoria.git
```

---

### 🗝️ Opção B: Deploy Key (recomendado para produção)

1. No EasyPanel, gere uma SSH key (ou use uma existente)

2. Adicione a chave pública no GitHub:
   - Vá em Settings > Deploy keys > Add deploy key
   - Cole a chave pública
   - Marque "Allow write access" se precisar push

3. No EasyPanel, use URL SSH:
```
git@github.com:leandrobosaipo/instagram-stories-curadoria.git
```

---

### 🌐 Opção C: App GitHub no EasyPanel

1. No EasyPanel, vá em **Integrations > GitHub**
2. Autorize o app GitHub
3. Selecione o repositório
4. Crie o serviço apontando para o repo

---

## 3) Variáveis de ambiente (EasyPanel)

Use os campos do `.env.vps.example`.

### Obrigatórias:
| Variável | Descrição |
|----------|-----------|
| `TARGET_PROFILE` | Perfil IG (ex: `perrenguematogrosso`) |
| `COOKIES_FILE` | Caminho do cookie (ex: `/app/data/instagram-cookies.txt`) |
| `OUTPUT_DIR` | Saída das imagens (ex: `/app/data/reels-media`) |
| `STATE_FILE` | Estado de deduplicação (ex: `/app/data/reels-media-state.json`) |
| `IG_APP_ID` | App ID do Instagram (default: `936619743392459`) |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram |
| `TELEGRAM_CHAT_ID` | Chat ID de destino |
| `TESSERACT_BIN` | Caminho do Tesseract (ex: `/usr/bin/tesseract`) |
| `RULES_FILE` | Regras de curadoria (ex: `/app/scripts/curadoria/rules.json`) |
| `SENT_STATE_FILE` | Estado de envio (ex: `/app/data/curadoria/telegram-sent-state.json`) |

---

## 4) Volumes persistentes

Monte pelo menos:
- `/app/data` — armazena cookies, state, imagens
- `/app/logs` — logs de execução

**Sem volume:** perde deduplicação e histórico.

---

## 5) Serviço principal

- **Build:** Dockerfile
- **Command:**
  ```
  python scripts/curadoria/run_editorial_pipeline.py
  ```

---

## 6) Cron no EasyPanel

- **Expressão:** `0 * * * *` (a cada 1h)
- **Comando:**
  ```
  python scripts/curadoria/run_editorial_pipeline.py
  ```

---

## 7) Teste inicial

1. Execute o job manualmente 1x no EasyPanel
2. Verifique logs
3. Confirme recebimento no Telegram

---

## 8) Troubleshooting

| Erro | Solução |
|------|---------|
| `403 Telegram` | `chat_id` errado ou sem `/start` no bot |
| `tesseract not found` | Ajustar `TESSERACT_BIN` para `/usr/bin/tesseract` |
| `Permission denied (deploy key)` | Adicionar chave pública no GitHub Deploy Keys |
| `Authentication failed` | Token expirado ou sem escopo `repo` |
| Sem novos memes | Stories expiraram ou já vistos (`seen_story_ids`) |

---

## 9) Cookie do Instagram

O cookie precisa ser atualizado periodicamente (quando expirar).

**Passos:**
1. Logue no Instagram pelo navegador
2. Exporte cookies em formato Netscape
3. Cole em `/app/data/instagram-cookies.txt` (via volume ou editor do EasyPanel)

---

## Checklist de Deploy

- [ ] Repo clonado no EasyPanel (via PAT, Deploy Key ou App)
- [ ] Variáveis de ambiente configuradas
- [ ] Volumes montados (`/app/data`, `/app/logs`)
- [ ] Cookie IG em `/app/data/instagram-cookies.txt`
- [ ] Build executado com sucesso
- [ ] Teste manual OK
- [ ] Cron configurado (`0 * * * *`)
- [ ] Confirmação de memes no Telegram
