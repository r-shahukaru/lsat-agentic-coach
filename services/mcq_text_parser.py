import os
import re
from typing import Dict, Tuple, Optional

def _read_normalized_text(source_folder: str) -> Optional[str]:
    path = os.path.join(source_folder, "_combined_ocr_normalized.txt")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def parse_normalized_mcq(source_folder: str) -> Dict:
    """
    Returns:
      {
        "passage": str | None,
        "question": str,
        "options": {"A": str, "B": str, "C": str, "D": str, "E": str}
      }
    Works off _combined_ocr_normalized.txt (your deterministic output).
    """
    text = _read_normalized_text(source_folder)
    if not text:
        return {"passage": None, "question": "", "options": {}}

    # Prefer content after PAGE BREAK if present
    if "----- PAGE BREAK -----" in text:
        _, after = text.split("----- PAGE BREAK -----", 1)
        block = after.strip()
        passage_part = text.split("----- PAGE BREAK -----", 1)[0].strip()
        passage = passage_part if passage_part else None
    else:
        block = text.strip()
        passage = None

    # Find first "A)" occurrence
    m = re.search(r"(^|\n)\s*A\)\s+", block)
    if not m:
        # no options found
        return {"passage": passage, "question": block.strip(), "options": {}}

    q_part = block[:m.start()].strip()

    # Extract A–E option text
    # Capture everything after each label until next label or end
    opt_pattern = re.compile(
        r"(^|\n)\s*([A-E])\)\s+(.*?)(?=(\n\s*[A-E]\)\s+)|\Z)",
        re.DOTALL
    )

    options = {}
    for match in opt_pattern.finditer(block):
        letter = match.group(2)
        content = match.group(3).strip()
        # Collapse internal newlines
        content = re.sub(r"\s*\n\s*", " ", content).strip()
        options[letter] = content

    return {"passage": passage, "question": q_part, "options": options}
