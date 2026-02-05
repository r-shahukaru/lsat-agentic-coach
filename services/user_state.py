import os
import time
from typing import Optional
from datetime import datetime, timezone

from services.local_storage import (
    save_json_to_file,
    load_json_from_file,
    append_jsonl,
    read_jsonl,
)


BASE_DIR = "data"
PROFILE_DIR = os.path.join(BASE_DIR, "user-profiles")

ATTEMPTS_DIR = os.path.join("data", "user-attempts")

def log_attempt(user_id: str, attempt: dict) -> None:
    attempt = dict(attempt)
    attempt.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    path = os.path.join(ATTEMPTS_DIR, user_id, "attempts.jsonl")
    append_jsonl(path, attempt)


def _profile_path(user_id: str) -> str:
    return os.path.join(PROFILE_DIR, user_id, "profile.json")


def _attempt_path(user_id: str, mcq_id: str, timestamp: str) -> str:
    return os.path.join(ATTEMPTS_DIR, user_id, "attempts", mcq_id, f"{timestamp}.json")


def _attempt_dir(user_id: str) -> str:
    return os.path.join(ATTEMPTS_DIR, user_id, "attempts")


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_profile(user_id: str) -> dict:
    return load_json_from_file(_profile_path(user_id), default={})


def save_profile(user_id: str, profile: dict):
    save_json_to_file(_profile_path(user_id), profile)


def build_attempt(
    user_id: str,
    mcq_id: str,
    selected: str,
    is_correct: Optional[bool],
    confidence: int,
    time_spent_sec: int,
    notes: Optional[str] = "",
    mode: str = "practice",
) -> dict:
    return {
        "user_id": user_id,
        "mcq_id": mcq_id,
        "timestamp_utc": utc_now_iso(),
        "selected": selected,
        "is_correct": is_correct,
        "confidence": int(confidence),
        "time_spent_sec": int(time_spent_sec),
        "notes": notes,
        "mode": mode,
    }


def log_attempt(user_id: str, attempt: dict):
    mcq_id = attempt["mcq_id"]
    timestamp = int(time.time())
    file_path = _attempt_path(user_id, mcq_id, str(timestamp))
    save_json_to_file(file_path, attempt)

    # Update profile with last attempt
    profile = get_profile(user_id)
    profile["last_seen_mcq_id"] = mcq_id
    profile["last_attempt_utc"] = attempt["timestamp_utc"]
    save_profile(user_id, profile)


def list_attempts(user_id: str, limit: int = 50) -> list[dict]:
    path = os.path.join(ATTEMPTS_DIR, user_id, "attempts.jsonl")
    items = read_jsonl(path, limit=limit)
    # most recent first for convenience
    return list(reversed(items))


    # Sort newest first
    attempts.sort(key=lambda x: x.get("timestamp_utc", ""), reverse=True)
    return attempts[:limit]
