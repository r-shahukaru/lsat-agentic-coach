"""
scripts/audit_subtypes_from_blobs.py

Pulls N MCQ JSON blobs from question-metadata and compares:
- stem_rule label (deterministic)
- existing stored subtype (if present)
- fresh model+judge subtype (optional)

Writes a report JSON locally.

Usage:
  python -m scripts.audit_subtypes_from_blobs --prefix "user01/mcqs/" --limit 20 --out audit_report.json
"""

from __future__ import annotations

import os
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

from services.storage_blob import get_blob_storage_from_env, download_blob_bytes, list_blobs
from services.subtype_classifier import (
    detect_subtype_from_stem,
    classify_subtype_with_guardrails,
)

def main() -> None:
    load_dotenv(".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="user01/mcqs/")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--out", default="audit_report.json")
    parser.add_argument("--run_model", action="store_true", help="Also run model+judge classification fresh")
    args = parser.parse_args()

    container = os.getenv("BLOB_CONTAINER_MCQS", "question-metadata")
    storage = get_blob_storage_from_env()

    blobs = list_blobs(storage, container, prefix=args.prefix)[: args.limit]

    rows = []
    mismatch_count = 0

    for name in blobs:
        raw = download_blob_bytes(storage, container, name)
        mcq = json.loads(raw.decode("utf-8"))

        question = mcq.get("question", "")
        options = mcq.get("options", {})

        stem_label = detect_subtype_from_stem(question)
        stored_label = mcq.get("subtype")

        fresh = None
        if args.run_model:
            fresh = classify_subtype_with_guardrails(question, options)

        mismatch = False
        # Compare stem rule vs stored subtype when stem rule exists
        if stem_label and stored_label and stem_label != stored_label:
            mismatch = True

        if mismatch:
            mismatch_count += 1

        rows.append(
            {
                "blob": name,
                "stem_label": stem_label,
                "stored_label": stored_label,
                "stored_confidence": mcq.get("subtype_confidence"),
                "stored_judge_verdict": mcq.get("judge_verdict"),
                "stored_judge_reason": mcq.get("judge_reason"),
                "fresh_model": fresh,  # dict or None
                "mismatch_stem_vs_stored": mismatch,
            }
        )

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "container": container,
        "prefix": args.prefix,
        "limit": args.limit,
        "mismatch_stem_vs_stored_count": mismatch_count,
        "rows": rows,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Wrote {args.out}")
    print(f"Checked: {len(rows)} blobs")
    print(f"Stem vs stored mismatches: {mismatch_count}\n")

if __name__ == "__main__":
    main()
