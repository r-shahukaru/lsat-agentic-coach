"""
scripts/ingest_section_question_folders.py

Ingests q1..qN folders inside a section directory and writes a run report.

Usage:
  python -m scripts.ingest_section_question_folders --section_dir "./data/local_images/lsat102/section1" --q_max 26 --user_id user01 --out section1_report.json
"""

from __future__ import annotations

import os
import json
import argparse
from datetime import datetime, timezone

from scripts.ingest_one_question_folder import ingest_question_folder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section_dir", required=True)
    parser.add_argument("--q_max", type=int, default=26)
    parser.add_argument("--user_id", default="user01")
    parser.add_argument("--out", default="section_report.json")
    args = parser.parse_args()

    results = []
    ok = 0
    fail = 0

    for i in range(1, args.q_max + 1):
        folder = os.path.join(args.section_dir, f"q{i}")
        if not os.path.isdir(folder):
            results.append({"q": i, "folder": folder, "status": "SKIP", "error": "Missing folder"})
            print(f"⏭️  SKIP q{i} (missing folder)")
            continue

        try:
            out = ingest_question_folder(folder=folder, user_id=args.user_id)
            results.append({"q": i, "folder": folder, "status": "OK", "output": out})
            ok += 1
            print(f"✅ OK  q{i} -> {out.get('subtype')}")
        except Exception as e:
            results.append({"q": i, "folder": folder, "status": "FAIL", "error": str(e)})
            fail += 1
            print(f"❌ FAIL q{i} -> {e}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "section_dir": args.section_dir,
        "q_max": args.q_max,
        "user_id": args.user_id,
        "ok": ok,
        "fail": fail,
        "results": results,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Wrote {args.out} | OK={ok} FAIL={fail}\n")


if __name__ == "__main__":
    main()
