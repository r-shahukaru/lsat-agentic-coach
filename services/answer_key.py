import os
import json

def load_answer_key(exam: str) -> dict:
    path = os.path.join("data", "answer-keys", exam, f"{exam}.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
