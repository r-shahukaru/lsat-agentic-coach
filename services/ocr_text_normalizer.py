from __future__ import annotations

import re
from typing import List, Dict, Tuple


def _clean(text: str) -> str:
    # This is intentionally conservative. We don’t try to “beautify”, just remove junk.
    t = text

    # Common OCR noise you showed (~ underscores, weird punctuation spacing)
    t = t.replace("~", " ").replace("_", " ")
    t = re.sub(r"[ \t]+", " ", t)

    # Make sure file markers start on their own lines (we inserted them earlier)
    t = re.sub(r"\s*(----- FILE:)", r"\n\1", t)

    # Normalize line breaks
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)

    return t.strip()


def _find_question_block(text: str) -> Tuple[str, str]:
    """
    Splits combined OCR into:
      passage_text, question_and_options_text
    Heuristic: first line that looks like "1." or "12." starts the question block.
    """
    m = re.search(r"(^|\n)\s*\d+\.\s+", text)
    if not m:
        return text, ""
    idx = m.start()
    return text[:idx].strip(), text[idx:].strip()


def _split_options_unlabeled(block: str) -> Tuple[str, List[str]]:
    """
    Given question+options block without A-E labels, try to split:
      stem, [opt1..opt5]
    Strategy:
      - first line is usually "1. <stem>"
      - then 4 option lines (from mcq-1)
      - then last option line appears in mcq-2
    """
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]

    if not lines:
        return "", []

    # Stem usually begins with "1."
    stem = lines[0]
    rest = lines[1:]

    # Sometimes OCR merges stem into multiple lines; keep pulling until we hit option-ish sentences.
    # This heuristic: options tend to start with capital letter and be full sentences.
    # If your OCR tends to keep the stem in one line, this won’t do much.
    while rest and len(stem) < 180 and not rest[0].startswith(("A)", "B)", "C)", "D)", "E)")) and not re.match(r"^[A-E]\)?\s", rest[0]):
        # stop if it looks like an option (sentence-ish)
        # (this is intentionally mild; we’d rather leave stem short than swallow an option)
        break

    # Now treat each remaining line as an option candidate
    return stem, rest

def _extract_options_from_correctness_markers(qblock: str):
    """
    Handles OCR patterns like:
      A INCORRECT
      option text...

      OR

      A
      INCORRECT
      option text...

    Returns (stem, opts) where opts are option texts in order.
    """

    lines = [ln.strip() for ln in qblock.splitlines()]
    is_marker_word = lambda x: x.upper() in {"CORRECT", "INCORRECT"}
    is_letter = lambda x: re.fullmatch(r"[A-E]", x) is not None

    # Step 1: find first marker position
    first_marker_idx = None
    i = 0
    while i < len(lines):
        ln = lines[i]

        # Case 1: "A INCORRECT"
        if re.fullmatch(r"[A-E]\s+(CORRECT|INCORRECT)", ln, re.IGNORECASE):
            first_marker_idx = i
            break

        # Case 2: "A" + "INCORRECT"
        if is_letter(ln) and i + 1 < len(lines) and is_marker_word(lines[i + 1]):
            first_marker_idx = i
            break

        i += 1

    if first_marker_idx is None:
        return None, None

    # Stem = everything before first marker
    stem = "\n".join([l for l in lines[:first_marker_idx] if l]).strip()

    opts = []
    i = first_marker_idx

    while i < len(lines):
        ln = lines[i]

        # detect marker (both formats)
        if re.fullmatch(r"[A-E]\s+(CORRECT|INCORRECT)", ln, re.IGNORECASE):
            i += 1
        elif is_letter(ln) and i + 1 < len(lines) and is_marker_word(lines[i + 1]):
            i += 2
        else:
            i += 1
            continue

        # collect option text
        buf = []
        while i < len(lines):
            nxt = lines[i]
            if (
                re.fullmatch(r"[A-E]\s+(CORRECT|INCORRECT)", nxt, re.IGNORECASE)
                or (is_letter(nxt) and i + 1 < len(lines) and is_marker_word(lines[i + 1]))
            ):
                break
            if nxt:
                buf.append(nxt)
            i += 1

        if buf:
            opts.append(" ".join(buf).strip())

    if len(opts) < 4:
        return None, None

    return stem, opts[:5]



def ensure_ae_labels(combined_text: str) -> str:
    """
    Converts OCR into a stable A) .. E) format.

    Deterministic-first:
    1) If A) B) already exist => leave it alone.
    2) If "A CORRECT / B INCORRECT" marker style exists => rebuild options from that.
    3) Else fall back to unlabeled splitting.
    """
    text = _clean(combined_text)
    passage, qblock = _find_question_block(text)

    if not qblock:
        return text

    # If A) B) exist already, don’t touch it
    if re.search(r"(^|\n)\s*A\)\s+", qblock) and re.search(r"(^|\n)\s*B\)\s+", qblock):
        return text

    # NEW: handle "A INCORRECT / text / B INCORRECT / text ..." style
    stem2, opts2 = _extract_options_from_correctness_markers(qblock)
    if stem2 is not None and opts2 is not None:
        labels = ["A)", "B)", "C)", "D)", "E)"]
        labeled_opts = [f"{labels[i]} {opts2[i]}" for i in range(min(5, len(opts2)))]
        rebuilt_q = "\n".join([stem2, ""] + labeled_opts)
        final = passage.strip() + "\n\n----- PAGE BREAK -----\n\n" + rebuilt_q.strip()
        return final.strip()

    # FALLBACK: your existing unlabeled split
    stem, opts = _split_options_unlabeled(qblock)

    if len(opts) < 4:
        return text

    opts = opts[:5]

    labels = ["A)", "B)", "C)", "D)", "E)"]
    labeled_opts = [f"{labels[i]} {opt}" for i, opt in enumerate(opts)]
    rebuilt_q = "\n".join([stem, ""] + labeled_opts)

    final = passage.strip() + "\n\n----- PAGE BREAK -----\n\n" + rebuilt_q.strip()
    return final.strip()


