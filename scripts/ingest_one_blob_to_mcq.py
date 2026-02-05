import os
import json
from services.local_storage import load_image_bytes, save_question_json
from scripts.ocr_one_blob_bytes import run_read_ocr_on_bytes
from services.mcq_parser import parse_lsac_ocr_text
from services.subtype_classifier import classify_subtype_with_guardrails

def process_one_image(local_path: str, user_id: str = "user01") -> dict:
    image_name = os.path.basename(local_path)
    print("[DEBUG] Image name:", image_name)

    # OCR
    image_bytes = load_image_bytes(local_path)
    ocr_text = run_read_ocr_on_bytes(image_bytes)

    # Parse
    question_mcq = parse_lsac_ocr_text(ocr_text)
    question_id = question_mcq.get("question_id") or image_name.replace(".png", "")
    question_mcq["question_id"] = question_id

    # Subtype tag
    subtype = classify_subtype_with_guardrails(question_mcq)
    question_mcq.update(subtype)

    # Save to local storage
    save_question_json(user_id, question_id, question_mcq)

    return {
        "path": local_path,
        "question_id": question_id,
        "stem": question_mcq.get("question"),
        "subtype": question_mcq.get("subtype")
    }
