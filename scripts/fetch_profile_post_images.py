#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values


def run_gram_posts(session_id: str, csrf_token: str, ds_user_id: str, username: str, limit: int = 80):
    cmd = [
        "gram",
        "--session-id",
        session_id,
        "--csrf-token",
        csrf_token,
        "--ds-user-id",
        ds_user_id,
        "posts",
        username,
        "-n",
        str(limit),
        "--json",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout)[-1200:])
    return json.loads(p.stdout)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"downloaded": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"downloaded": []}


def save_state(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ext_from_url(url: str) -> str:
    low = url.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if ext in low:
            return ext
    return ".jpg"


def main():
    ap = argparse.ArgumentParser(description="Baixa apenas imagens de posts do perfil (feed/carrossel).")
    ap.add_argument("--env", default=".env.posts")
    args = ap.parse_args()

    cfg = dotenv_values(Path(args.env).expanduser().resolve())
    username = (cfg.get("TARGET_PROFILE") or "").strip()
    session_id = (cfg.get("IG_SESSION_ID") or "").strip()
    csrf = (cfg.get("IG_CSRF_TOKEN") or "").strip()
    ds = (cfg.get("IG_DS_USER_ID") or "").strip()
    out_dir = Path(cfg.get("OUTPUT_DIR", "./data/posts-images")).expanduser().resolve()
    state_file = Path(cfg.get("STATE_FILE", "./data/posts-images-state.json")).expanduser().resolve()
    limit = int(cfg.get("POSTS_LIMIT", "80"))

    if not all([username, session_id, csrf, ds]):
        raise SystemExit("Defina TARGET_PROFILE, IG_SESSION_ID, IG_CSRF_TOKEN e IG_DS_USER_ID")

    posts = run_gram_posts(session_id, csrf, ds, username, limit=limit)
    state = load_state(state_file)
    seen = set(state.get("downloaded", []))

    today = datetime.now().strftime("%Y-%m-%d")
    base = out_dir / username / today
    base.mkdir(parents=True, exist_ok=True)

    new_files = []
    all_ids = set(seen)

    for p in posts:
        ptype = p.get("type")
        shortcode = p.get("shortcode") or p.get("id") or "unknown"
        media = p.get("media") or []

        # queremos apenas imagem de post/carrossel
        if ptype not in ("image", "carousel"):
            continue

        for idx, m in enumerate(media, start=1):
            mtype = (m.get("type") or "").lower()
            url = (m.get("url") or "").strip()
            if mtype != "image" or not url:
                continue

            key = f"{shortcode}:{idx}:{url}"
            if key in seen:
                continue

            ext = ext_from_url(url)
            fname = f"{shortcode}_{idx}{ext}"
            dest = base / fname

            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            dest.write_bytes(data)

            new_files.append(str(dest))
            all_ids.add(key)

    state["downloaded"] = sorted(all_ids)
    state["last_run"] = datetime.now().isoformat()
    state["target_profile"] = username
    state["new_count"] = len(new_files)
    save_state(state_file, state)

    print(f"OK - novas imagens de posts: {len(new_files)}")
    for f in new_files[:30]:
        print("NEW:", f)


if __name__ == "__main__":
    main()
