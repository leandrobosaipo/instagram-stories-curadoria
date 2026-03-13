#!/usr/bin/env python3
import argparse
import json
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"downloaded_files": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"downloaded_files": []}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def list_images(root: Path) -> set[str]:
    if not root.exists():
        return set()
    out = set()
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            out.add(str(p.resolve()))
    return out


def run_download(url: str, output_template: str, cookies_file: Path, timeout_sec: int, mode: str) -> tuple[int, str]:
    cmd = [
        "yt-dlp",
        "--cookies",
        str(cookies_file),
        "--sleep-requests",
        "2",
        "--min-sleep-interval",
        "2",
        "--max-sleep-interval",
        "5",
        "--retries",
        "3",
        "--fragment-retries",
        "3",
        "--socket-timeout",
        "25",
        "--no-overwrites",
        "--merge-output-format",
        "mp4",
        "-S",
        "vcodec:h264,acodec:aac",
    ]
    if mode == "images":
        cmd += ["--match-filter", "ext = 'jpg' | ext = 'jpeg' | ext = 'png' | ext = 'webp'"]
    elif mode == "videos":
        cmd += ["--match-filter", "ext = 'mp4' | ext = 'webm' | ext = 'mkv'"]
    cmd += ["-o", output_template, url]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    log = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode, log


def main() -> int:
    parser = argparse.ArgumentParser(description="Baixa stories privados via cookies + yt-dlp.")
    parser.add_argument("--env", default=".env", help="Arquivo .env")
    parser.add_argument("--mode", choices=["images", "videos", "auto"], default="images", help="images: só imagem | videos: só vídeo | auto: tenta imagem, se não houver baixa vídeo")
    args = parser.parse_args()

    cfg = dotenv_values(Path(args.env).expanduser().resolve())

    target_profile = (cfg.get("TARGET_PROFILE") or "").strip()
    output_dir = Path(cfg.get("OUTPUT_DIR", "./data/stories")).expanduser().resolve()
    state_file = Path(cfg.get("STATE_FILE", "./data/state.json")).expanduser().resolve()
    cookies_file = Path(cfg.get("COOKIES_FILE", "./data/instagram-cookies.txt")).expanduser().resolve()
    max_attempts = int(cfg.get("MAX_ATTEMPTS", "3"))

    if not target_profile:
        raise SystemExit("Defina TARGET_PROFILE no .env")
    if not cookies_file.exists():
        raise SystemExit(f"Cookie file não encontrado: {cookies_file}")

    date_dir = datetime.now().strftime("%Y-%m-%d")
    target_dir = output_dir / target_profile / date_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    state = load_state(state_file)
    before = list_images(output_dir / target_profile)

    url = f"https://www.instagram.com/stories/{target_profile}/"
    output_template = str(target_dir / "%(upload_date|NA)s_%(id)s.%(ext)s")

    rc = 1
    logs = []

    primary_mode = args.mode if args.mode in {"images", "videos"} else "images"
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            wait_s = min(300, (2 ** attempt) * 10) + random.randint(5, 20)
            time.sleep(wait_s)
        rc, log = run_download(url, output_template, cookies_file, timeout_sec=240, mode=primary_mode)
        logs.append(f"=== tentativa {attempt} (modo={primary_mode}, rc={rc}) ===\n{log}")
        if rc == 0:
            break

    after = list_images(output_dir / target_profile)
    new_files = sorted(after - before)

    # fallback: modo auto baixa vídeos se não houver imagem nova
    if args.mode == "auto" and len(new_files) == 0:
        before_all = set(str(p.resolve()) for p in (output_dir / target_profile).rglob("*") if p.is_file())
        rc2, log2 = run_download(url, output_template, cookies_file, timeout_sec=240, mode="videos")
        logs.append(f"=== fallback videos (rc={rc2}) ===\n{log2}")
        after_all = set(str(p.resolve()) for p in (output_dir / target_profile).rglob("*") if p.is_file())
        video_new = sorted(after_all - before_all)
        if video_new:
            new_files = video_new
            rc = rc2

    # guarda estado cumulativo (qualquer mídia baixada)
    all_now = set(str(p.resolve()) for p in (output_dir / target_profile).rglob("*") if p.is_file())
    old = set(state.get("downloaded_files", []))
    merged = sorted(old.union(all_now))
    state["downloaded_files"] = merged
    state["last_run"] = datetime.now().isoformat()
    state["target_profile"] = target_profile
    state["last_rc"] = rc
    state["new_count"] = len(new_files)
    state["last_logs_tail"] = "\n\n".join(logs)[-5000:]
    save_state(state_file, state)

    print(f"OK - novas imagens baixadas: {len(new_files)}")
    for f in new_files[:20]:
        print(f"NEW: {f}")

    return 0 if len(new_files) >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
