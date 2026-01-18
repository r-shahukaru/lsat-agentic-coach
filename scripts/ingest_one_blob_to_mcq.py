"""
scripts/ingest_one_blob_to_mcq.py

End-to-end for ONE question:
Blob image -> OCR -> MCQ parse -> store MCQ JSON in question-metadata

Usage:
  python -m scripts.ingest_one_blob_to_mcq --blob_name "user01/uploads/....png"
"""

from __future__ import annotations

import os
import json
import argparse
from uuid import uuid4
from dotenv import load_dotenv

from services.storage_blob import get_blob_storage_from_env, download_blob_bytes, upload_json_to_blob
from services.mcq_parser import parse_lsac_ocr_text
from scripts.ocr_one_blob_bytes import run_read_ocr_on_bytes  # reusing the OCR function

from services.subtype_classifier import classify_subtype_with_guardrails

def process_one_image(local_path: str, user_id: str = "user01") -> dict:
    """
    Running the end-to-end pipeline for one local screenshot and returning a compact summary.
    """
    load_dotenv()

    images_container = os.getenv("BLOB_CONTAINER_IMAGES", "question-images")
    meta_container = os.getenv("BLOB_CONTAINER_MCQS", "question-metadata")

    storage = get_blob_storage_from_env()

    # Uploading the raw screenshot first so everything is traceable and reproducible.
    img_id = str(uuid4())
    image_blob = f"{user_id}/uploads/{img_id}.png"
    up = storage.upload_file(container=images_container, file_path=local_path, blob_name=image_blob)

    # Downloading bytes back from the blob for OCR (keeps the pipeline consistent with production).
    img_bytes = download_blob_bytes(storage, images_container, image_blob)

    # OCR -> parsed question/options
    ocr_text = run_read_ocr_on_bytes(img_bytes)
    question, options = parse_lsac_ocr_text(ocr_text)

    # Subtype classification with guardrails
    subtype_result = classify_subtype_with_guardrails(question, options)

    # Writing the MCQ JSON artifact
    mcq_id = str(uuid4())
    mcq_blob = f"{user_id}/mcqs/{mcq_id}.json"

    mcq = {
        "id": mcq_id,
        "source_local_path": local_path,
        "source_blob_name": image_blob,
        "question": question,
        "options": options,
        "subtype": subtype_result["subtype"],
        "subtype_confidence": subtype_result["confidence"],
        "subtype_rationale": subtype_result["rationale"],
        "judge_verdict": subtype_result["judge_verdict"],
        "judge_reason": subtype_result["judge_reason"],
        "ocr_text": ocr_text,
    }

    mcq_url = upload_json_to_blob(storage, meta_container, mcq_blob, mcq)

    return {
        "source_local_path": local_path,
        "image_blob": up.blob_name,
        "image_url": up.blob_url,
        "mcq_id": mcq_id,
        "mcq_blob": mcq_blob,
        "mcq_url": mcq_url,
        "subtype": mcq["subtype"],
        "judge_verdict": mcq["judge_verdict"],
    }


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--local_path", required=True)
    parser.add_argument("--user_id", default=os.getenv("DEFAULT_USER_ID", "user01"))
    args = parser.parse_args()

    out = process_one_image(local_path=args.local_path, user_id=args.user_id)
    print(json.dumps(out, indent=2))



if __name__ == "__main__":
    main()
