#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

import requests
from dotenv import dotenv_values


def load_netscape_cookies(path: Path) -> dict:
    cookies = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            cookies[parts[5]] = parts[6]
    return cookies


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"seen_story_ids": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"seen_story_ids": []}


def save_state(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_best_image(item: dict) -> str | None:
    candidates = (((item.get("image_versions2") or {}).get("candidates")) or [])
    if not candidates:
        return None
    best = max(candidates, key=lambda c: (c.get("width", 0) * c.get("height", 0)))
    return best.get("url")


def pick_best_video(item: dict) -> str | None:
    versions = item.get("video_versions") or []
    if not versions:
        return None
    best = max(versions, key=lambda v: v.get("width", 0) * v.get("height", 0))
    return best.get("url")


def download_bytes(session: requests.Session, url: str, path: Path):
    r = session.get(url, timeout=45)
    r.raise_for_status()
    path.write_bytes(r.content)


def main():
    ap = argparse.ArgumentParser(description="Coleta stories via endpoint reels_media (UI-like).")
    ap.add_argument("--env", default=".env.reels")
    ap.add_argument("--mode", choices=["images", "all"], default="images")
    args = ap.parse_args()

    cfg = dotenv_values(Path(args.env).expanduser().resolve())
    target = (cfg.get("TARGET_PROFILE") or "").strip()
    cookies_file = Path(cfg.get("COOKIES_FILE", "./data/instagram-cookies.txt")).expanduser().resolve()
    out_dir = Path(cfg.get("OUTPUT_DIR", "./data/reels-media")).expanduser().resolve()
    state_file = Path(cfg.get("STATE_FILE", "./data/reels-media-state.json")).expanduser().resolve()
    app_id = (cfg.get("IG_APP_ID") or "936619743392459").strip()

    if not target:
        raise SystemExit("Defina TARGET_PROFILE")
    if not cookies_file.exists():
        raise SystemExit(f"Cookies não encontrado: {cookies_file}")

    cookies = load_netscape_cookies(cookies_file)

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
        "Accept": "*/*",
        "X-IG-App-ID": app_id,
    })
    s.cookies.update(cookies)

    # resolve user_id
    r = s.get(f"https://www.instagram.com/api/v1/users/web_profile_info/?username={target}", timeout=30)
    r.raise_for_status()
    user_id = str(r.json()["data"]["user"]["id"])

    # stories via endpoint da UI
    rr = s.get(f"https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={user_id}", timeout=30)
    rr.raise_for_status()
    items = (((rr.json().get("reels") or {}).get(user_id) or {}).get("items") or [])

    state = load_state(state_file)
    seen = set(str(x) for x in state.get("seen_story_ids", []))

    day = datetime.now().strftime("%Y-%m-%d")
    base = out_dir / target / day
    base.mkdir(parents=True, exist_ok=True)

    new_files = []
    mt_count = {"image": 0, "video": 0}

    for item in items:
        story_id = str(item.get("id") or "")
        if not story_id:
            continue

        media_type = item.get("media_type")
        is_image = media_type == 1
        is_video = media_type == 2

        if is_image:
            mt_count["image"] += 1
        elif is_video:
            mt_count["video"] += 1

        if story_id in seen:
            continue

        if is_image:
            url = pick_best_image(item)
            if not url:
                continue
            path = base / f"{story_id}.jpg"
            download_bytes(s, url, path)
            new_files.append(str(path))
            seen.add(story_id)
            continue

        if args.mode == "all" and is_video:
            vurl = pick_best_video(item)
            if not vurl:
                continue
            vpath = base / f"{story_id}.mp4"
            download_bytes(s, vurl, vpath)

            # frame para curadoria
            jpath = base / f"{story_id}.jpg"
            subprocess.run([
                "ffmpeg", "-y", "-i", str(vpath), "-vf", "thumbnail", "-frames:v", "1", str(jpath)
            ], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            new_files.append(str(vpath))
            if jpath.exists():
                new_files.append(str(jpath))
            seen.add(story_id)

    state["seen_story_ids"] = sorted(seen)
    state["last_run"] = datetime.now().isoformat()
    state["target_profile"] = target
    state["items_total"] = len(items)
    state["items_media_type"] = mt_count
    state["new_files_count"] = len(new_files)
    save_state(state_file, state)

    print(f"TOTAL items: {len(items)} | image={mt_count['image']} video={mt_count['video']}")
    print(f"OK - novos arquivos: {len(new_files)}")
    for f in new_files[:40]:
        print("NEW:", f)


if __name__ == "__main__":
    main()
