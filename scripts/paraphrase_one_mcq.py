"""
scripts/paraphrase_one_mcq.py

Downloads an MCQ JSON from question-metadata, runs paraphrase guardrails,
and writes the updated JSON back to the same blob.

Usage:
  python -m scripts.paraphrase_one_mcq --mcq_blob "user01/mcqs/<id>.json"
"""

from __future__ import annotations

import os
import json
import argparse
from dotenv import load_dotenv

from services.storage_blob import get_blob_storage_from_env, download_blob_bytes, upload_json_to_blob
from services.paraphraser import paraphrase_with_guardrails


def main() -> None:
    load_dotenv(".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--mcq_blob", required=True)
    args = parser.parse_args()

    meta_container = os.getenv("BLOB_CONTAINER_MCQS", "question-metadata")
    storage = get_blob_storage_from_env()

    raw = download_blob_bytes(storage, meta_container, args.mcq_blob)
    mcq = json.loads(raw.decode("utf-8"))

    result = paraphrase_with_guardrails(mcq["question"], mcq["options"])

    mcq["paraphrase_status"] = result["status"]
    mcq["paraphrase_judge"] = result["judge"]

    if result["status"] == "OK":
        mcq["paraphrased_question"] = result["paraphrased_question"]
        mcq["paraphrased_options"] = result["paraphrased_options"]

    url = upload_json_to_blob(storage, meta_container, args.mcq_blob, mcq)

    print("\n✅ Paraphrase step complete")
    print("MCQ blob:", args.mcq_blob)
    print("Status :", result["status"])
    if result["status"] != "OK":
        print("Judge  :", result["judge"])
    print("URL    :", url)
    print("")


if __name__ == "__main__":
    main()
