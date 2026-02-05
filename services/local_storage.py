import os
import json
from typing import Any, Optional


def load_json_from_file(path: str, default: Optional[Any] = None) -> Any:
    """
    Loads JSON from disk. Returns `default` if the file doesn't exist
    or is empty/invalid JSON.
    """
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_to_file(path: str, data: Any) -> None:
    """
    Safely writes JSON data to disk, creating parent directories if needed.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_jsonl(path: str, obj: Any) -> None:
    """
    Appends one JSON object as a single line (JSONL). Creates parent dirs.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path: str, limit: Optional[int] = None) -> list[Any]:
    """
    Reads JSONL file into a list. If limit is provided, returns most recent `limit` items.
    """
    if not os.path.isfile(path):
        return []
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    if limit is not None and len(items) > limit:
        return items[-limit:]
    return items
