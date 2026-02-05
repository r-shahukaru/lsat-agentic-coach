def parse_lsac_ocr_text(ocr_text: str) -> dict:
    return {
        "question_id": "temp_qid",
        "question": ocr_text.strip(),
        "options": ["A", "B", "C", "D", "E"],
        "answer": None,
        "subtype": None,
    }
