#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from curadoria.rule_engine import CuradoriaRules


def ocr_text(img: Path) -> str:
    tesseract_bin = os.getenv("TESSERACT_BIN", "tesseract")
    cmd = [tesseract_bin, str(img), "stdout", "-l", "por+eng", "--psm", "6"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (p.stdout or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--rules", default="scripts/curadoria/rules.json")
    args = ap.parse_args()

    inp = Path(args.input).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    rules = CuradoriaRules(Path(args.rules))

    (out / "meme").mkdir(parents=True, exist_ok=True)
    (out / "noticia-propaganda").mkdir(parents=True, exist_ok=True)
    (out / "revisar").mkdir(parents=True, exist_ok=True)

    report = []
    imgs = sorted([p for p in inp.glob("*.jpg")])
    for img in imgs:
        txt = ocr_text(img)
        label, details = rules.classify(txt)
        dest = out / label / img.name
        shutil.copy2(img, dest)
        report.append(
            {
                "file": img.name,
                "label": label,
                "scores": details.get("scores", {}),
                "forced_label": details.get("forced_label"),
                "text_preview": txt[:220],
                "matches": details.get("matches", []),
            }
        )

    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {"meme": 0, "noticia-propaganda": 0, "revisar": 0}
    for r in report:
        counts[r["label"]] += 1
    print(json.dumps({"total": len(report), "counts": counts, "out": str(out), "rules": str(Path(args.rules).resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
