from __future__ import annotations

import os
import csv
import json
import argparse


def norm_section(val: str) -> int:
    s = str(val).strip().lower()
    # accepts: "3", "s3", "section3"
    s = s.replace("section", "").replace("s", "")
    return int(s)


def norm_qno(val: str) -> int:
    # accepts: "21", "q21", "Q21"
    s = str(val).strip().lower().replace("q", "")
    return int(s)


def norm_ans(val: str) -> str:
    s = str(val).strip().upper()
    if s and s[0] in "ABCDE":
        return s[0]
    raise ValueError(f"Invalid answer value: {val!r}")


def detect_columns(fieldnames: list[str]) -> tuple[str, str, str]:
    """
    Returns (section_col, qno_col, ans_col) by heuristics.
    Works with common headers like:
      section, question_no, answer
      Section, Q, Correct
      s, q, key
    """
    lower = [f.strip().lower() for f in fieldnames]

    def pick(candidates: list[str]) -> str:
        for cand in candidates:
            if cand in lower:
                return fieldnames[lower.index(cand)]
        return ""

    section_col = pick(["section", "sec", "s"])
    qno_col     = pick(["question_no", "question", "qno", "q", "questionnumber", "question number"])
    ans_col     = pick(["answer", "ans", "key", "correct", "correct_answer", "correct answer"])

    if not (section_col and qno_col and ans_col):
        raise ValueError(f"Could not detect columns from header: {fieldnames}")

    return section_col, qno_col, ans_col


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exam", required=True)
    ap.add_argument("--csv", required=True, help="Path to answer key CSV/TSV")
    ap.add_argument("--out", required=True, help="Output JSON path")
    ap.add_argument("--delimiter", default="", help="Optional: ',' or '\\t'. If empty, auto-detect.")
    args = ap.parse_args()

    exam = args.exam.strip()
    in_path = args.csv
    out_path = args.out

    if not os.path.isfile(in_path):
        raise FileNotFoundError(in_path)

    # Auto-detect delimiter: tab if file looks TSV, else comma
    delimiter = args.delimiter or "\t"


    mapping: dict[str, str] = {}

    with open(in_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError("CSV/TSV has no header row.")
        section_col, qno_col, ans_col = detect_columns(reader.fieldnames)

        for row in reader:
            sec = norm_section(row[section_col])
            qno = norm_qno(row[qno_col])
            ans = norm_ans(row[ans_col])

            qid = f"{exam}-s{sec}-q{qno:02d}"
            mapping[qid] = ans

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"✅ Wrote {out_path} with {len(mapping)} entries.")
    # quick sanity print
    for k in list(mapping.keys())[:5]:
        print("  ", k, "->", mapping[k])


if __name__ == "__main__":
    main()
