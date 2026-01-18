"""
services/mcq_parser.py

Parses OCR output into an MCQ structure.
Designed for LSAT-style questions with options A-E.
"""

from __future__ import annotations

import re
from typing import Tuple, Dict

from services.mcq_repair_llm import repair_question_and_options

_OPTION_RE = re.compile(r'^\s*([A-E])\s*[\)\.\:]*\s*$', re.IGNORECASE)

def _normalize_lines(text: str) -> list[str]:
    lines = text.splitlines()
    return [re.sub(r"\s+", " ", ln).strip() for ln in lines]


def _extract_question_block_for_repair(text: str, max_chars: int = 1200) -> str:
    """
    Minimizing what we send to the LLM:
    - Prefer starting at the first numbered question like '2.'
    - Otherwise take the tail end of the text
    """
    m = re.search(r"(^|\n)\s*\d+\.\s", text)
    if m:
        block = text[m.start():]
    else:
        block = text

    block = block.strip()

    # Hard cap to keep the LLM call small and stable
    if len(block) > max_chars:
        block = block[-max_chars:]

    return block


def parse_lsac_ocr_text(ocr_text: str) -> Tuple[str, Dict[str, str]]:
    """
    Parsing OCR output into (question, options).
    Tries deterministic parsing first.
    Falls back to LLM-based structure repair ONLY if option markers are missing.
    """
    try:
        # -------------------------------
        # Rule-based parsing (your existing logic)
        # -------------------------------
        lines = _normalize_lines(ocr_text)

        marker_positions = {}
        for i, ln in enumerate(lines):
            m = _OPTION_RE.match(ln)
            if m:
                letter = m.group(1).upper()
                if letter not in marker_positions:
                    marker_positions[letter] = i

        if not all(k in marker_positions for k in ["A", "B", "C", "D", "E"]):
            raise ValueError("Could not detect option markers (A-E) reliably")

        idxs = [marker_positions[k] for k in ["A", "B", "C", "D", "E"]]
        if idxs != sorted(idxs):
            raise ValueError("Option markers detected but not in expected order (A-E)")

        a_i, b_i, c_i, d_i, e_i = idxs

        question_block = "\n".join([ln for ln in lines[:a_i] if ln]).strip()
        if not question_block:
            raise ValueError("Question text parsed empty")

        def collect(start: int, end: int) -> str:
            chunk = [ln for ln in lines[start:end] if ln]
            return " ".join(chunk).strip()

        options = {
            "A": collect(a_i + 1, b_i),
            "B": collect(b_i + 1, c_i),
            "C": collect(c_i + 1, d_i),
            "D": collect(d_i + 1, e_i),
            "E": collect(e_i + 1, len(lines)),
        }

        if any(not v for v in options.values()):
            raise ValueError("Detected option markers but one or more options parsed empty")

        return question_block, options

    except ValueError as e:
        # ------------------------------------
        # Targeted LLM fallback (structure only)
        # ------------------------------------
        if "Could not detect option markers (A-E) reliably" not in str(e):
            raise  # rethrow unrelated errors

        question_block = _extract_question_block_for_repair(ocr_text)

        result = repair_question_and_options(question_block)

        if isinstance(result, dict) and result.get("status") == "NEEDS_REVIEW":
            raise ValueError("LLM repair returned NEEDS_REVIEW")

        # repair_question_and_options returns {"question": ..., "options": {...}}
        try:
            return result["question"], result["options"]
        except Exception:
            raise ValueError("LLM repair returned invalid payload")