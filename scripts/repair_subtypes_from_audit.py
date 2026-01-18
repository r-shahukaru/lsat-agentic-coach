"""
scripts/repair_subtypes_from_audit.py

Reads an audit_report.json, and for each mismatch:
- recomputes subtype via classify_subtype_with_guardrails
- writes updated subtype fields back to the same MCQ blob

Usage:
  python -m scripts.repair_subtypes_from_audit --audit audit_report.json
"""

from __future__ import annotations

import json
import os
import argparse
from dotenv import load_dotenv

from services.storage_blob import (
    get_blob_storage_from_env,
    download_blob_bytes,
    upload_json_to_blob,
)
from services.subtype_classifier import classify_subtype_with_guardrails

def main() -> None:
    load_dotenv(".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    args = parser.parse_args()

    container = os.getenv("BLOB_CONTAINER_MCQS", "question-metadata")
    storage = get_blob_storage_from_env()

    with open(args.audit, "r", encoding="utf-8") as f:
        report = json.load(f)

    rows = report.get("rows", [])
    to_fix = [r for r in rows if r.get("mismatch_stem_vs_stored")]

    print(f"\nFound {len(to_fix)} mismatches to fix.\n")

    for r in to_fix:
        blob = r["blob"]

        raw = download_blob_bytes(storage, container, blob)
        mcq = json.loads(raw.decode("utf-8"))

        question = mcq.get("question", "")
        options = mcq.get("options", {})

        fixed = classify_subtype_with_guardrails(question, options)

        # Write back fields (keeping your existing names)
        mcq["subtype"] = fixed["subtype"]
        mcq["subtype_confidence"] = fixed["confidence"]
        mcq["subtype_rationale"] = fixed["rationale"]
        mcq["judge_verdict"] = fixed["judge_verdict"]
        mcq["judge_reason"] = fixed["judge_reason"]

        upload_json_to_blob(storage, container, blob, mcq)
        print(f"✅ Updated: {blob} -> {fixed['subtype']}")

    print("\nDone.\n")

if __name__ == "__main__":
    main()
