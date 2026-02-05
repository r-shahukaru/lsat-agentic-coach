from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple, Dict

from streamlit import text

from scripts.ocr_one_blob_bytes import run_read_ocr_on_bytes
from services.local_storage import load_image_bytes, save_question_json
from services.mcq_parser import parse_lsac_ocr_text
from services.subtype_classifier import classify_subtype_with_guardrails
from services.ocr_text_normalizer import ensure_ae_labels


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def _tokens(name: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", name.lower()) if t]


def _classify(filename: str) -> Optional[str]:
    # Kept intentionally simple: filename hints only
    lower = filename.lower()
    toks = _tokens(lower)

    if "passage" in lower or "passages" in lower or "stimulus" in lower or "p" in toks:
        return "passage"
    if "mcq" in lower or "mcqs" in lower or "question" in lower or "q" in toks:
        return "mcq"
    return None


def _extract_nums(filename: str) -> List[int]:
    return [int(n) for n in re.findall(r"\d+", filename.lower())]


def _sort_key(filename: str) -> Tuple[int, List[int], str]:
    # passage first, then mcq, then unknown; numeric order next; then lexical
    kind = _classify(filename)
    kind_rank = 2
    if kind == "passage":
        kind_rank = 0
    elif kind == "mcq":
        kind_rank = 1

    nums = _extract_nums(filename)
    if not nums:
        nums = [9999]

    return (kind_rank, nums, filename.lower())


def _parse_exam_section_q(question_dir: str) -> Tuple[str, str, int]:
    """
    Expects path like: data/local_images/lsat102/section1/q14
    Returns: (exam, section, q_num)
    """
    parts = os.path.normpath(question_dir).split(os.sep)

    # Find ".../<exam>/<section>/<qdir>"
    # This is intentionally defensive; it just finds the last 3 meaningful parts.
    exam = parts[-3]
    section = parts[-2]
    qdir = parts[-1]

    sec_num = int(re.findall(r"\d+", section)[0])  # section1 -> 1
    q_num = int(re.findall(r"\d+", qdir)[0])       # q14 -> 14

    section_tag = f"s{sec_num}"
    return exam, section_tag, q_num


def process_one_question_folder(question_dir: str, user_id: str = "user01") -> Dict:
    # List images inside the folder (this is the unit of work)
    filenames = [
        f for f in os.listdir(question_dir)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
    ]
    filenames.sort(key=_sort_key)

    if not filenames:
        raise ValueError(f"No images found in: {question_dir}")

    exam, section_tag, q_num = _parse_exam_section_q(question_dir)
    question_id = f"{exam}-{section_tag}-q{q_num:02d}"

    # OCR everything and stitch it into one stream (same trick as the old project)
    chunks: List[str] = []
    debug_chunks: List[str] = []

    for f in filenames:
        path = os.path.join(question_dir, f)
        print(f"[DEBUG] OCR part: {f}")

        # ---- OCR cache (so we never re-pay OpenAI for the same image)
        cache_path = os.path.join(question_dir, f"._ocr_cache_{f}.txt")

        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as fp:
                text = fp.read()
        else:
            img_bytes = load_image_bytes(path)
            text = run_read_ocr_on_bytes(img_bytes)
            with open(cache_path, "w", encoding="utf-8") as fp:
                fp.write(text)

        if text:
            chunks.append(text.strip() + "\n")

        # Debug version keeps file boundaries (not used for parsing)
        debug_chunks.append(f"\n\n----- FILE: {f} -----\n")
        debug_chunks.append(text if text else "")

    combined_text = "\n".join(chunks)

    # Write debug OCR (for inspection only)
    debug_path = os.path.join(question_dir, "_combined_ocr_debug.txt")
    with open(debug_path, "w", encoding="utf-8") as fp:
        fp.write("".join(debug_chunks))

        # Normalize (adds A–E labels when OCR didn't capture them)
    normalized_text = ensure_ae_labels(combined_text)

    # Save normalized OCR too (this is what we actually parse)
    norm_path = os.path.join(question_dir, "_combined_ocr_normalized.txt")
    with open(norm_path, "w", encoding="utf-8") as fp:
        fp.write(normalized_text)

    # Parse once from the normalized OCR
    question_mcq = parse_lsac_ocr_text(normalized_text)



    # Ensure canonical id (stable across runs)
    question_mcq["question_id"] = question_id
    question_mcq["exam"] = exam
    question_mcq["section"] = section_tag
    question_mcq["question_no"] = q_num
    question_mcq["source_folder"] = question_dir
    question_mcq["parts"] = filenames

    # Subtype tag (your existing guardrail classifier)
    subtype = classify_subtype_with_guardrails(question_mcq)
    question_mcq.update(subtype)

    # Save one JSON per question folder
    save_question_json(user_id, question_id, question_mcq)

    return {
        "question_id": question_id,
        "question_dir": question_dir,
        "parts": filenames,
        "debug_path": debug_path,
        "stem": question_mcq.get("question"),
        "subtype": question_mcq.get("subtype"),
    }
