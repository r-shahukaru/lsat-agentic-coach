"""services/user_state.py

Blob-backed user state for the Streamlit app.

Design goals:
- Dead simple storage model (append-only attempts + small profile doc).
- Works even if answer keys aren't available yet (is_correct can be null).
- Compatible with the existing Blob wrapper style in services/storage_blob.py.

Containers (defaults):
- user-profiles
- user-attempts

Override via env vars:
- AZURE_CONTAINER_USER_PROFILES
- AZURE_CONTAINER_USER_ATTEMPTS
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.storage_blob import (
    AzureBlobStorage,
    download_json_from_blob,
    list_blob_names,
    upload_json_to_blob,
)


DEFAULT_PROFILES_CONTAINER = "user-profiles"
DEFAULT_ATTEMPTS_CONTAINER = "user-attempts"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _profiles_container() -> str:
    return os.getenv("AZURE_CONTAINER_USER_PROFILES", DEFAULT_PROFILES_CONTAINER).strip() or DEFAULT_PROFILES_CONTAINER


def _attempts_container() -> str:
    return os.getenv("AZURE_CONTAINER_USER_ATTEMPTS", DEFAULT_ATTEMPTS_CONTAINER).strip() or DEFAULT_ATTEMPTS_CONTAINER


@dataclass
class Attempt:
    user_id: str
    mcq_id: str
    timestamp_utc: str
    selected: str
    is_correct: Optional[bool]
    confidence: int
    time_spent_sec: int
    notes: str
    mode: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "mcq_id": self.mcq_id,
            "timestamp_utc": self.timestamp_utc,
            "selected": self.selected,
            "is_correct": self.is_correct,
            "confidence": self.confidence,
            "time_spent_sec": self.time_spent_sec,
            "notes": self.notes,
            "mode": self.mode,
        }


def build_attempt(
    *,
    user_id: str,
    mcq_id: str,
    selected: str,
    confidence: int,
    time_spent_sec: int,
    notes: str = "",
    mode: str = "practice",
    is_correct: Optional[bool] = None,
    timestamp_utc: Optional[str] = None,
) -> Attempt:
    """Building an Attempt object with sane defaults."""

    ts = timestamp_utc or utc_now_iso()
    selected_norm = (selected or "").strip().upper()
    if selected_norm not in {"A", "B", "C", "D", "E"}:
        raise ValueError("selected must be one of A/B/C/D/E")

    conf = int(confidence)
    if conf < 1:
        conf = 1
    if conf > 5:
        conf = 5

    spent = int(time_spent_sec)
    if spent < 0:
        spent = 0

    return Attempt(
        user_id=user_id,
        mcq_id=mcq_id,
        timestamp_utc=ts,
        selected=selected_norm,
        is_correct=is_correct,
        confidence=conf,
        time_spent_sec=spent,
        notes=(notes or "").strip(),
        mode=(mode or "practice").strip() or "practice",
    )


def get_profile(storage: AzureBlobStorage, user_id: str) -> Dict[str, Any]:
    """Reading profile.json for a user or returning a minimal default profile."""

    blob_name = f"{user_id}/profile.json"
    profile = download_json_from_blob(
        storage=storage,
        container=_profiles_container(),
        blob_name=blob_name,
        default=None,
    )

    if not profile:
        return {
            "user_id": user_id,
            "created_utc": utc_now_iso(),
            "last_seen_mcq_id": None,
            "last_attempt_utc": None,
            "settings": {},
        }

    # Normalizing keys for safety.
    profile.setdefault("user_id", user_id)
    profile.setdefault("settings", {})
    profile.setdefault("last_seen_mcq_id", None)
    profile.setdefault("last_attempt_utc", None)
    profile.setdefault("created_utc", utc_now_iso())
    return profile


def save_profile(storage: AzureBlobStorage, user_id: str, profile: Dict[str, Any]) -> str:
    """Saving the profile back to Blob."""

    blob_name = f"{user_id}/profile.json"
    return upload_json_to_blob(
        storage=storage,
        container=_profiles_container(),
        blob_name=blob_name,
        payload=profile,
    )


def log_attempt(storage: AzureBlobStorage, user_id: str, attempt: Dict[str, Any]) -> str:
    """Append-only attempt logging + lightweight profile pointer updates."""

    mcq_id = str(attempt.get("mcq_id", "")).strip() or "unknown"
    timestamp_utc = str(attempt.get("timestamp_utc", "")).strip() or utc_now_iso()

    # Making the blob name sortable + unique.
    safe_ts = timestamp_utc.replace(":", "-")
    attempt_id = uuid.uuid4().hex[:10]
    blob_name = f"{user_id}/attempts/{mcq_id}/{safe_ts}_{attempt_id}.json"

    url = upload_json_to_blob(
        storage=storage,
        container=_attempts_container(),
        blob_name=blob_name,
        payload=attempt,
    )

    # Updating profile pointers.
    profile = get_profile(storage=storage, user_id=user_id)
    profile["last_seen_mcq_id"] = mcq_id
    profile["last_attempt_utc"] = timestamp_utc
    save_profile(storage=storage, user_id=user_id, profile=profile)

    return url


def list_attempts(storage: AzureBlobStorage, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Listing recent attempts for a user.

    Notes:
    - We list blob names and then download the most recent ones.
    - Blob listing order isn't guaranteed. We sort by blob name (timestamp prefix).
    """

    prefix = f"{user_id}/attempts/"
    names = list_blob_names(storage=storage, container=_attempts_container(), prefix=prefix)

    # Sorting descending by name, because the name starts with timestamp.
    names_sorted = sorted(names, reverse=True)
    names_sorted = names_sorted[: max(0, int(limit))]

    attempts: List[Dict[str, Any]] = []
    for blob_name in names_sorted:
        payload = download_json_from_blob(
            storage=storage,
            container=_attempts_container(),
            blob_name=blob_name,
            default=None,
        )
        if payload:
            attempts.append(payload)

    return attempts
