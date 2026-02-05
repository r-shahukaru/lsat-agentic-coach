"""
scripts/build_question_index.py

Builds an index file from processed outputs so the app can load quickly.

Assumes processed layout:
  data/processed/<user>/<exam>/<section>/<qXX>/*.json
"""

from __future__ import annotations

import os
import json
import argparse
from typing import Dict, List


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed_root", required=True, help="e.g. data/processed/user01/lsat102")
    parser.add_argument("--out", default="data/processed/user01/lsat102/index.json")
    args = parser.parse_args()

    root = args.processed_root
    items: List[Dict] = []

    for section in sorted(os.listdir(root)):
        section_path = os.path.join(root, section)
        if not os.path.isdir(section_path):
            continue

        for qdir in sorted(os.listdir(section_path)):
            qpath = os.path.join(section_path, qdir)
            if not os.path.isdir(qpath):
                continue

            # We just record whatever exists; app will handle missing gracefully
            passage_json = os.path.join(qpath, "passage.json")
            questions_json = os.path.join(qpath, "questions.json")

            items.append(
                {
                    "section": section,
                    "question_folder": qdir,
                    "path": qpath,
                    "passage_json": passage_json if os.path.exists(passage_json) else None,
                    "questions_json": questions_json if os.path.exists(questions_json) else None,
                }
            )

    index = {"processed_root": root, "count": len(items), "items": items}

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"✅ Wrote index: {args.out} | count={len(items)}")


if __name__ == "__main__":
    main()