#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import requests
from dotenv import dotenv_values

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data"


def _load_env() -> dict:
    env_file = os.getenv("ENV_FILE")
    if env_file:
        p = Path(env_file).expanduser().resolve()
        return {k: v for k, v in dotenv_values(p).items() if v is not None}

    merged = {}
    for name in [".env", ".env.reels", ".env.telegram.editorial"]:
        p = BASE / name
        if p.exists():
            merged.update({k: v for k, v in dotenv_values(p).items() if v is not None})
    return merged


def tg_request(token: str, method: str, data=None, files=None, timeout=30):
    url = f"https://api.telegram.org/bot{token}/{method}"
    r = requests.post(url, data=data, files=files, timeout=timeout) if method.startswith("send") else requests.get(url, timeout=timeout)
    r.raise_for_status()
    payload = r.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error ({method}): {payload}")
    return payload


def load_sent(path: Path) -> dict:
    if not path.exists():
        return {"sent": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_sent(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def run_cmd(cmd: list[str]):
    subprocess.run(cmd, check=True, cwd=str(BASE))


def main():
    parser = argparse.ArgumentParser(description="Pipeline editorial: coleta, OCR, curadoria, Telegram")
    parser.add_argument("--initial-run", action="store_true", help="Primeira execução: envia TODOS os memes de TODOS os dias")
    parser.add_argument("--skip-fetch", action="store_true", help="Pula coleta (usa dados já existentes)")
    parser.add_argument("--dry-run", action="store_true", help="Não envia para Telegram, só mostra o que seria enviado")
    args = parser.parse_args()

    cfg = _load_env()

    target = (cfg.get("TARGET_PROFILE") or "").strip()
    output_dir = Path(cfg.get("OUTPUT_DIR") or (DATA / "reels-media")).expanduser().resolve()
    rules_file = Path(cfg.get("RULES_FILE") or (BASE / "scripts/curadoria/rules.json")).expanduser().resolve()
    sent_state = Path(cfg.get("SENT_STATE_FILE") or (DATA / "curadoria/telegram-sent-state.json")).expanduser().resolve()

    token = (cfg.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (cfg.get("TELEGRAM_CHAT_ID") or "").strip()
    silent = (cfg.get("TELEGRAM_SILENT") or "false").strip().lower() == "true"
    max_per_run = int((cfg.get("TELEGRAM_MAX_PER_RUN") or "50").strip())  # aumenta para initial run

    if not target:
        raise SystemExit("TARGET_PROFILE não definido")
    if not token or not chat_id:
        raise SystemExit("Preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")

    me = tg_request(token, "getMe")
    bot_name = me["result"].get("username", "(sem-username)")

    env_for_sub = os.environ.copy()
    if env_for_sub.get("TESSERACT_BIN") is None and cfg.get("TESSERACT_BIN"):
        env_for_sub["TESSERACT_BIN"] = str(cfg.get("TESSERACT_BIN"))

    # coleta (pula se --skip-fetch)
    if not args.skip_fetch:
        if (BASE / ".env.reels").exists():
            run_cmd(["python", "scripts/fetch_stories_reels_media.py", "--env", ".env.reels"])
        else:
            tmp_env = BASE / ".env.reels.generated"
            tmp_env.write_text(
                "\n".join([
                    f"TARGET_PROFILE={target}",
                    f"COOKIES_FILE={cfg.get('COOKIES_FILE','/app/data/instagram-cookies.txt')}",
                    f"OUTPUT_DIR={output_dir}",
                    f"STATE_FILE={cfg.get('STATE_FILE', str(DATA / 'reels-media-state.json'))}",
                    f"IG_APP_ID={cfg.get('IG_APP_ID', '936619743392459')}",
                ]) + "\n",
                encoding="utf-8",
            )
            try:
                run_cmd(["python", "scripts/fetch_stories_reels_media.py", "--env", str(tmp_env)])
            finally:
                tmp_env.unlink(missing_ok=True)

    input_root = output_dir / target
    if not input_root.exists():
        raise SystemExit(f"Sem diretório de entrada: {input_root}")

    day_dirs = sorted([p for p in input_root.iterdir() if p.is_dir()])
    if not day_dirs:
        raise SystemExit("Nenhuma pasta diária encontrada em reels-media")

    # Define dias a processar
    if args.initial_run:
        days_to_process = [d.name for d in day_dirs]
        print(f"🚀 INITIAL RUN: processando {len(days_to_process)} dias: {days_to_process}")
    else:
        days_to_process = [day_dirs[-1].name]

    # Estado de envio
    state = load_sent(sent_state)
    sent = set() if args.initial_run else set(state.get("sent", []))

    total_sent = 0
    all_results = []

    for day in days_to_process:
        in_dir = input_root / day
        out_dir = DATA / "curadoria" / day

        # OCR + classificação
        subprocess.run(
            [
                "python",
                "scripts/classify_story_images.py",
                "--input", str(in_dir),
                "--output", str(out_dir),
                "--rules", str(rules_file),
            ],
            check=True,
            cwd=str(BASE),
            env=env_for_sub,
        )

        meme_dir = out_dir / "meme"
        if not meme_dir.exists():
            continue

        meme_files = sorted(meme_dir.glob("*.jpg"))
        to_send = [p for p in meme_files if str(p) not in sent][:max_per_run]

        if not to_send:
            continue

        # Aviso no Telegram
        if not args.dry_run:
            tg_request(token, "sendMessage", data={
                "chat_id": chat_id,
                "text": f"📅 {day}: {len(meme_files)} memes | Enviando {len(to_send)} {'(DRY RUN)' if args.dry_run else ''}",
                "disable_notification": str(silent).lower(),
            })

        # Envia fotos
        sent_now = []
        for img in to_send:
            if args.dry_run:
                print(f"  [DRY RUN] {img.name}")
                sent_now.append(str(img))
            else:
                with img.open("rb") as f:
                    tg_request(token, "sendPhoto", data={
                        "chat_id": chat_id,
                        "caption": f"meme · {day} · {img.name}",
                        "disable_notification": str(silent).lower(),
                    }, files={"photo": f})
                sent_now.append(str(img))

        sent.update(sent_now)
        total_sent += len(sent_now)
        all_results.append({"day": day, "total": len(meme_files), "sent": len(sent_now)})

    # Salva estado
    state["sent"] = sorted(sent)
    state["last_run"] = datetime.now().isoformat()
    state["last_day"] = days_to_process[-1]
    state["last_sent_count"] = total_sent
    state["initial_run"] = args.initial_run
    save_sent(sent_state, state)

    # Resumo final
    result = {
        "ok": True,
        "bot": bot_name,
        "initial_run": args.initial_run,
        "days_processed": len(days_to_process),
        "total_sent": total_sent,
        "details": all_results,
        "chat_id": chat_id,
        "dry_run": args.dry_run,
    }
    print(json.dumps(result, ensure_ascii=False))

    # Mensagem final no Telegram
    if not args.dry_run and total_sent > 0:
        tg_request(token, "sendMessage", data={
            "chat_id": chat_id,
            "text": f"✅ Pipeline concluído\n📊 {len(days_to_process)} dias | {total_sent} memes enviados",
            "disable_notification": str(silent).lower(),
        })


if __name__ == "__main__":
    main()
