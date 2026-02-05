from __future__ import annotations

import os
import re
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List

from scripts.ingest_one_question_folder_local import process_one_question_folder


def _sorted_sections(root: str) -> List[str]:
    secs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
    secs.sort(key=lambda s: int(re.findall(r"\d+", s)[0]))
    return secs


def _sorted_qdirs(section_path: str) -> List[str]:
    qdirs = [d for d in os.listdir(section_path) if os.path.isdir(os.path.join(section_path, d))]
    qdirs.sort(key=lambda q: int(re.findall(r"\d+", q)[0]))
    return qdirs


def list_question_folders_in_lsat_order(input_root: str) -> List[str]:
    # This enforces your required order:
    # section1/q1..q26, then section2/q1..q26, then section3, then section4
    folders: List[str] = []
    for section in _sorted_sections(input_root):
        section_path = os.path.join(input_root, section)
        for qdir in _sorted_qdirs(section_path):
            folders.append(os.path.join(section_path, qdir))
    return folders


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_root", required=True, help="e.g. data/local_images/lsat102")
    parser.add_argument("--user", default="user01")
    parser.add_argument("--limit", type=int, default=0, help="0 = no limit")
    parser.add_argument("--out", default="run_report_tree.json")
    parser.add_argument("--dry_run", action="store_true")
    args = parser.parse_args()

    q_folders = list_question_folders_in_lsat_order(args.input_root)

    if args.limit and args.limit > 0:
        q_folders = q_folders[:args.limit]

    if args.dry_run:
        print("---- DRY RUN (question folders in final order) ----")
        for p in q_folders:
            print(p)
        print(f"\nTotal folders: {len(q_folders)}")
        return

    report: Dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "input_root": args.input_root,
        "user_id": args.user,
        "total_folders": len(q_folders),
        "ok": 0,
        "fail": 0,
        "items": [],
    }

    for folder in q_folders:
        print(f"\n[DEBUG] FOLDER: {folder}")

        try:
            result = process_one_question_folder(question_dir=folder, user_id=args.user)
            report["ok"] += 1
            report["items"].append({"status": "OK", "folder": folder, "result": result})
            print(f"✅ OK  {result.get('question_id')}")
        except Exception as e:
            report["fail"] += 1
            report["items"].append({"status": "FAIL", "folder": folder, "error": repr(e)})
            print(f"❌ FAIL {folder} -> {repr(e)}")

    report["finished_at"] = datetime.now(timezone.utc).isoformat()

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Wrote {args.out} | OK={report['ok']} FAIL={report['fail']}")


if __name__ == "__main__":
    main()
