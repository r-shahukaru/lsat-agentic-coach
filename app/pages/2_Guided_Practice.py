import os
import random
import time
import json
from pathlib import Path
from typing import Optional

import html

import streamlit as st

from services.user_state import build_attempt, log_attempt
from services.answer_key import load_answer_key
from services.mcq_text_parser import parse_normalized_mcq

BASE_DIR = "data"
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")

def list_processed_questions(user_id: str, exam: str) -> list[Path]:
    user_dir = Path(PROCESSED_DIR) / user_id
    if not user_dir.exists():
        return []
    # Your repo has many formats; simplest reliable filter:
    # lsat102-s1-q01.json etc. in data/processed/user01/
    return sorted(user_dir.glob(f"{exam}-s*-q*.json"))

def load_processed_mcq(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

st.title("📝 Guided Practice")

user_id = st.selectbox("User", ["user01"], index=0)
exam = st.selectbox("Exam", ["lsat102"], index=0)

answer_key = load_answer_key(exam)
files = list_processed_questions(user_id, exam)

if not files:
    st.warning(f"No processed questions found for {exam} in {PROCESSED_DIR}/{user_id}.")
    st.stop()

if st.button("Load Next Question"):
    picked = random.choice(files)
    mcq = load_processed_mcq(picked)

    parsed = parse_normalized_mcq(mcq["source_folder"])
    st.session_state.current_mcq = mcq
    st.session_state.parsed_mcq = parsed
    st.session_state.timer_start = time.time()
    st.session_state.selected = None
    st.session_state.notes = ""
    st.session_state.confidence = 3

mcq = st.session_state.get("current_mcq")
parsed = st.session_state.get("parsed_mcq")

if not mcq or not parsed:
    st.info("Click 'Load Next Question' to begin.")
    st.stop()

qid = mcq["question_id"]
st.caption(f"Question ID: `{qid}` | subtype: `{mcq.get('subtype','unknown')}`")

# Display passage if present
if parsed.get("passage"):
    st.subheader("Passage")
    st.markdown(
        f"<div style='white-space: pre-wrap; line-height: 1.6;'>{html.escape(parsed['passage'])}</div>",
        unsafe_allow_html=True
    )


st.subheader("Question")
st.write(parsed.get("question", "").strip())

opts = parsed.get("options", {})
if len(opts) != 5:
    st.warning("Options did not parse cleanly from normalized OCR text.")
    st.json(opts)

# Show options nicely
for letter in ["A","B","C","D","E"]:
    if letter in opts:
        st.markdown(f"**{letter}.** {opts[letter]}")

selected = st.radio("Choose your answer:", ["A", "B", "C", "D", "E"], key="selected")
confidence = st.slider("Confidence", 1, 5, key="confidence")
notes = st.text_area("Notes (optional)", key="notes")

if st.button("Submit"):
    correct = answer_key.get(qid)  # e.g. "C"
    is_correct = (selected == correct) if correct else None

    time_spent = int(time.time() - st.session_state.get("timer_start", time.time()))

    attempt = build_attempt(
        user_id=user_id,
        mcq_id=qid,
        selected=selected,
        is_correct=is_correct,
        confidence=confidence,
        time_spent_sec=time_spent,
        notes=notes,
        mode="practice",
    )

    # Add extra fields for tutor context (safe, local)
    attempt["exam"] = mcq.get("exam")
    attempt["section"] = mcq.get("section")
    attempt["question_no"] = mcq.get("question_no")
    attempt["correct_answer"] = correct

    log_attempt(user_id, attempt)

    # Make it available to Tutor Coach immediately
    st.session_state.last_attempt = attempt

    if is_correct is True:
        st.success(f"✅ Correct! ({selected})")
    elif is_correct is False:
        st.error(f"❌ Incorrect. You chose {selected}, correct is {correct}.")
    else:
        st.warning("Logged attempt, but no answer key match for this question_id.")

    st.info("Now go to **Tutor Coach** page to get the explanation.")
