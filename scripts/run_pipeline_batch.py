"""
scripts/run_pipeline_batch.py

Runs your end-to-end pipeline on a batch of local images and writes a run report.
- Continues on errors (does not crash the whole run)
- Saves per-file status + blob paths + error messages

Usage:
  python -m scripts.run_pipeline_batch --input_dir "./local_screenshots" --user "user01" --limit 20 --out run_report.json
"""
from __future__ import annotations

import os
import json
import argparse
from datetime import datetime, timezone

# TODO: replace this import with YOUR actual pipeline entrypoint function
# Example signature we want:
#   process_one_image(local_path: str, user_id: str) -> dict
from scripts.ingest_one_blob_to_mcq import process_one_image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--user", default="user01")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--out", default="run_report.json")
    args = parser.parse_args()

    files = []
    for root, _, filenames in os.walk(args.input_dir):
        for name in sorted(filenames):
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                files.append(os.path.join(root, name))


    files = files[: args.limit]

    results = []
    ok = 0
    fail = 0

    for path in files:
        try:
            out = process_one_image(local_path=path, user_id=args.user)
            results.append({"file": path, "status": "OK", "output": out})
            ok += 1
            print(f"✅ OK  {os.path.basename(path)}")
        except Exception as e:
            results.append({"file": path, "status": "FAIL", "error": str(e)})
            fail += 1
            print(f"❌ FAIL {os.path.basename(path)}  -> {e}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user": args.user,
        "input_dir": args.input_dir,
        "limit": args.limit,
        "ok": ok,
        "fail": fail,
        "results": results,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Wrote {args.out} | OK={ok} FAIL={fail}\n")


if __name__ == "__main__":
    main()
