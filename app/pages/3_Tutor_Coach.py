import streamlit as st
from services.user_state import list_attempts
from services.mcq_text_parser import parse_normalized_mcq
from services.answer_key import load_answer_key
from services.tutor_llm import build_tutor_prompt, tutor_response
import json
from pathlib import Path

st.title("🧠 Tutor Coach (Chat)")

user_id = st.selectbox("User", ["user01"], index=0)
exam = st.selectbox("Exam", ["lsat102"], index=0)

mcq = st.session_state.get("current_mcq")
last_attempt = st.session_state.get("last_attempt")

if not mcq or not last_attempt:
    st.info("Do a Guided Practice question first, then come back here.")
    st.stop()

qid = mcq["question_id"]

parsed = parse_normalized_mcq(mcq["source_folder"])
question_text = parsed.get("question", "")
options = parsed.get("options", {})

answer_key = load_answer_key(exam)
correct = last_attempt.get("correct_answer") or answer_key.get(qid)

chosen = last_attempt.get("selected")
subtype = mcq.get("subtype", "unknown")

# Build a tiny mistake memory
attempts = list_attempts(user_id, limit=50)
wrong = [a for a in attempts if a.get("is_correct") is False]
mistake_summary = ""
if wrong:
    # simplest memory: most recent 5 wrong question ids
    recent_wrong = [a["mcq_id"] for a in wrong[:5]]
    mistake_summary = "Recent wrong question_ids: " + ", ".join(recent_wrong)

st.caption(f"Question ID: `{qid}` | subtype: `{subtype}`")
st.markdown(f"**You chose:** `{chosen}`  \n**Correct:** `{correct}`")

with st.expander("Show question + options"):
    st.write(question_text)
    for k in ["A","B","C","D","E"]:
        if k in options:
            st.markdown(f"**{k}.** {options[k]}")

# Chat history
if "tutor_messages" not in st.session_state:
    st.session_state.tutor_messages = []

for msg in st.session_state.tutor_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt_hint = "Ask for a breakdown, traps, or a faster heuristic…"

user_msg = st.chat_input(prompt_hint)
if user_msg:
    st.session_state.tutor_messages.append({"role": "user", "content": user_msg})
    with st.chat_message("user"):
        st.markdown(user_msg)

    # If user asks anything, we respond with full tutoring context (still focused on chosen-wrong first)
    system, user = build_tutor_prompt(
        question=question_text,
        options=options,
        chosen=chosen,
        correct=correct,
        subtype=subtype,
        mistake_summary=mistake_summary,
    )
    # Add user question at the end
    user = user + "\n\nStudent follow-up question:\n" + user_msg

    with st.chat_message("assistant"):
        out = tutor_response(system, user)
        st.markdown(out)

    st.session_state.tutor_messages.append({"role": "assistant", "content": out})

# Auto-generate an explanation immediately (ASAP) when first opening
if st.button("Generate explanation now"):
    system, user = build_tutor_prompt(
        question=question_text,
        options=options,
        chosen=chosen,
        correct=correct,
        subtype=subtype,
        mistake_summary=mistake_summary,
    )
    out = tutor_response(system, user)
    st.session_state.tutor_messages.append({"role": "assistant", "content": out})
    st.rerun()
