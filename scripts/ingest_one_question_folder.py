"""
scripts/ingest_one_question_folder.py

Ingests ONE question folder (q1/q2/...) containing multiple screenshots that together
include the passage/question/options.

Strategy:
- Upload all images to blob for traceability
- OCR each image
- Concatenate OCR text in filename order
- Parse MCQ from combined OCR text
- Classify subtype with guardrails
- Store one MCQ JSON

Usage:
  python -m scripts.ingest_one_question_folder --folder "./data/local_images/lsat102/section1/q1" --user_id user01
"""

from __future__ import annotations

import os
import json
import argparse
from uuid import uuid4
from dotenv import load_dotenv

from services.storage_blob import get_blob_storage_from_env, download_blob_bytes, upload_json_to_blob
from scripts.ocr_one_blob_bytes import run_read_ocr_on_bytes
from services.mcq_parser import parse_lsac_ocr_text
from services.subtype_classifier import classify_subtype_with_guardrails


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def ingest_question_folder(folder: str, user_id: str = "user01") -> dict:
    load_dotenv()

    images_container = os.getenv("BLOB_CONTAINER_IMAGES", "question-images")
    meta_container = os.getenv("BLOB_CONTAINER_MCQS", "question-metadata")
    storage = get_blob_storage_from_env()

    # Reading all images in stable order (keeps deterministic behavior)
    files = sorted(
        [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(IMAGE_EXTS)]
    )
    if not files:
        raise ValueError(f"No images found in folder: {folder}")

    uploaded = []
    ocr_parts = []

    group_id = str(uuid4())

    for idx, path in enumerate(files, start=1):
        # Uploading each screenshot for traceability
        blob_name = f"{user_id}/uploads/{group_id}/part{idx:02d}{os.path.splitext(path)[1].lower()}"
        up = storage.upload_file(container=images_container, file_path=path, blob_name=blob_name)
        uploaded.append({"local_path": path, "blob": up.blob_name, "url": up.blob_url})

        # OCR each part (using bytes from blob to match prod behavior)
        img_bytes = download_blob_bytes(storage, images_container, blob_name)
        ocr_text = run_read_ocr_on_bytes(img_bytes)
        ocr_parts.append(ocr_text)

    combined_ocr = "\n\n----- PAGE BREAK -----\n\n".join(ocr_parts)

    # Dumping OCR to a local file for parser debugging (makes failures inspectable)
    debug_path = os.path.join(folder, "_combined_ocr_debug.txt")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(combined_ocr)

    # Parsing MCQ from combined OCR
    question, options = parse_lsac_ocr_text(combined_ocr)

    # Subtype classification
    subtype_result = classify_subtype_with_guardrails(question, options)

    # Store one MCQ JSON
    mcq_id = str(uuid4())
    mcq_blob = f"{user_id}/mcqs/{mcq_id}.json"

    mcq = {
        "id": mcq_id,
        "source_folder": folder,
        "source_images": uploaded,
        "question": question,
        "options": options,
        "subtype": subtype_result["subtype"],
        "subtype_confidence": subtype_result["confidence"],
        "subtype_rationale": subtype_result["rationale"],
        "judge_verdict": subtype_result["judge_verdict"],
        "judge_reason": subtype_result["judge_reason"],
        "ocr_text_combined": combined_ocr,
    }

    mcq_url = upload_json_to_blob(storage, meta_container, mcq_blob, mcq)

    return {
        "folder": folder,
        "mcq_id": mcq_id,
        "mcq_blob": mcq_blob,
        "mcq_url": mcq_url,
        "num_images": len(files),
        "subtype": mcq["subtype"],
        "judge_verdict": mcq["judge_verdict"],
    }


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--user_id", default=os.getenv("DEFAULT_USER_ID", "user01"))
    args = parser.parse_args()

    out = ingest_question_folder(folder=args.folder, user_id=args.user_id)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
