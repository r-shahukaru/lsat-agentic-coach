"""app/pages/2_Guided_Practice.py

Practice MVP:
- Load a random MCQ from Blob (question-metadata/<user_id>/mcqs/...).
- Render passage (if present), question stem, options A-E.
- Capture selection + confidence + time spent + notes.
- Log attempt to Blob (user-attempts) and update profile pointer (user-profiles).

This page intentionally avoids answer keys. `is_correct` is logged as null for now.
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st


# Ensuring imports work when Streamlit runs this file directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.storage_blob import get_blob_storage_from_env, download_json_from_blob, list_blob_names  # noqa: E402
from services.user_state import build_attempt, log_attempt, get_profile  # noqa: E402


DEFAULT_QMETA_CONTAINER = "question-metadata"


def _qmeta_container() -> str:
    return os.getenv("AZURE_CONTAINER_QUESTION_METADATA", DEFAULT_QMETA_CONTAINER).strip() or DEFAULT_QMETA_CONTAINER


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _extract_passage(mcq: Dict[str, Any]) -> Optional[str]:
    # Supporting a couple of likely field names.
    for key in ["passage", "stimulus", "context", "reading_passage"]:
        val = mcq.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _extract_question_text(mcq: Dict[str, Any]) -> str:
    for key in ["question", "stem", "prompt"]:
        val = mcq.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "(question missing)"


def _extract_options(mcq: Dict[str, Any]) -> Dict[str, str]:
    opts = mcq.get("options")
    if isinstance(opts, dict):
        out = {}
        for k in ["A", "B", "C", "D", "E"]:
            v = opts.get(k)
            out[k] = (v or "").strip()
        return out

    # Some pipelines store as list.
    if isinstance(opts, list):
        letters = ["A", "B", "C", "D", "E"]
        out = {}
        for i, letter in enumerate(letters):
            out[letter] = (opts[i] if i < len(opts) else "").strip()
        return out

    return {k: "" for k in ["A", "B", "C", "D", "E"]}


def _load_all_mcq_blob_names(storage, user_id: str) -> List[str]:
    prefix = f"{user_id}/mcqs/"
    return list_blob_names(storage=storage, container=_qmeta_container(), prefix=prefix)


def _load_random_mcq(storage, user_id: str) -> Dict[str, Any]:
    names = _load_all_mcq_blob_names(storage=storage, user_id=user_id)
    if not names:
        raise RuntimeError(f"No MCQs found in container '{_qmeta_container()}' with prefix '{user_id}/mcqs/'")

    chosen = random.choice(names)
    mcq = download_json_from_blob(storage=storage, container=_qmeta_container(), blob_name=chosen, default={})

    # Ensuring mcq_id exists.
    mcq_id = mcq.get("id") or mcq.get("mcq_id")
    if not mcq_id:
        # Fallback: derive from filename.
        mcq_id = Path(chosen).stem
        mcq["id"] = mcq_id

    mcq["_blob_name"] = chosen
    return mcq


def _reset_question_state() -> None:
    st.session_state.pop("current_mcq", None)
    st.session_state.pop("question_loaded_at", None)
    st.session_state.pop("selected_option", None)
    st.session_state.pop("confidence", None)
    st.session_state.pop("notes", None)


def main() -> None:
    st.title("Guided Practice")

    storage = get_blob_storage_from_env()

    user_id = st.selectbox("User", options=["user01"], index=0, key="user_id")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("Load next question", type="primary"):
            _reset_question_state()
            st.session_state["current_mcq"] = _load_random_mcq(storage=storage, user_id=user_id)
            st.session_state["question_loaded_at"] = _now_utc()

    with col2:
        if st.button("Reset", type="secondary"):
            _reset_question_state()

    with col3:
        profile = get_profile(storage=storage, user_id=user_id)
        st.caption(f"Last seen MCQ: {profile.get('last_seen_mcq_id') or '—'}")

    if "current_mcq" not in st.session_state:
        st.info("Click **Load next question** to begin.")
        return

    mcq = st.session_state["current_mcq"]
    passage = _extract_passage(mcq)
    question_text = _extract_question_text(mcq)
    options = _extract_options(mcq)

    st.divider()

    if passage:
        st.subheader("Passage")
        st.write(passage)

    st.subheader("Question")
    st.write(question_text)

    st.subheader("Options")

    option_labels = {k: f"{k}) {options.get(k,'').strip()}" for k in ["A", "B", "C", "D", "E"]}
    selected = st.radio(
        "Select an answer",
        options=["A", "B", "C", "D", "E"],
        format_func=lambda k: option_labels.get(k, k),
        key="selected_option",
        horizontal=False,
    )

    confidence = st.slider("Confidence", min_value=1, max_value=5, value=3, key="confidence")
    notes = st.text_area("Notes (optional)", key="notes")

    # Timing
    loaded_at: datetime = st.session_state.get("question_loaded_at") or _now_utc()
    st.session_state["question_loaded_at"] = loaded_at
    elapsed = int((_now_utc() - loaded_at).total_seconds())
    st.caption(f"Time on this question: ~{elapsed} sec")

    submitted = st.button("Submit", type="primary")

    if not submitted:
        return

    attempt_obj = build_attempt(
        user_id=user_id,
        mcq_id=str(mcq.get("id")),
        selected=selected,
        confidence=int(confidence),
        time_spent_sec=int(elapsed),
        notes=notes or "",
        mode="practice",
        is_correct=None,
    )

    url = log_attempt(storage=storage, user_id=user_id, attempt=attempt_obj.to_dict())

    st.success("Attempt saved.")
    st.caption(f"Logged to Blob: {url}")

    # Auto-load next question (fast feedback loop)
    _reset_question_state()
    st.session_state["current_mcq"] = _load_random_mcq(storage=storage, user_id=user_id)
    st.session_state["question_loaded_at"] = _now_utc()
    st.rerun()


# Lazy-load when button pressed (avoids listing blobs on every page refresh).
main()
