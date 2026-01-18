import sys
from pathlib import Path
import time
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from services.storage_blob import AzureBlobStorage, upload_json_to_blob
from services.user_state import utc_now_iso

# ---------- CONFIG ----------
COACH_CONTAINER = "user-coach-events"

# ---------- HELPERS ----------
def diagnose_reasoning(subtype: str, explanation: str) -> str:
    explanation = explanation.lower()

    if subtype in ["Strengthen", "Weaken"]:
        if "support" in explanation:
            return "Confused support with logical impact"
        if "felt right" in explanation:
            return "Intuition-based selection, not reasoning"
    if "because" not in explanation:
        return "No explicit reasoning articulated"

    return "Partial reasoning, needs structure"


def coach_tip(subtype: str) -> str:
    tips = {
        "Strengthen": "Look for the choice that closes the gap between premise and conclusion.",
        "Weaken": "Find the choice that introduces doubt about the argument’s core assumption.",
        "Flaw": "Describe what the argument *does wrong*, not what it fails to mention.",
        "Assumption": "Ask: what must be true for this argument to work at all?"
    }
    return tips.get(subtype, "Focus on identifying premises, conclusion, and the logical gap.")


# ---------- UI ----------
st.title("🧠 LSAT Coach")

st.markdown(
    "This coach helps you **improve your thinking**, not just your score. "
    "Answer honestly — that’s how it adapts."
)

storage = AzureBlobStorage.from_env()

user_id = st.selectbox("User", ["user01"], index=0)

mcq = st.session_state.get("current_mcq")
last_attempt = st.session_state.get("last_attempt")

if not mcq or not last_attempt:
    st.info("Practice a question first. Then come back here.")
    st.stop()

st.divider()

st.subheader("Reflect on your reasoning")

subtype = mcq.get("subtype", "Unknown")

st.markdown(f"**Question Type:** `{subtype}`")

user_explanation = st.text_area(
    "Why did you choose that answer?",
    placeholder="Explain your thinking in 1–2 sentences."
)

confidence = st.slider(
    "How confident were you when you chose it?",
    1, 5, last_attempt.get("confidence", 3)
)

if st.button("Get Coaching"):
    if not user_explanation.strip():
        st.warning("Please explain your reasoning first.")
        st.stop()

    issue = diagnose_reasoning(subtype, user_explanation)
    tip = coach_tip(subtype)

    st.divider()
    st.subheader("Coach Feedback")

    st.markdown(f"**Diagnosis:** {issue}")
    st.markdown(f"**Guidance:** {tip}")

    coach_event = {
        "user_id": user_id,
        "mcq_id": mcq.get("id"),
        "timestamp_utc": utc_now_iso(),
        "subtype": subtype,
        "user_explanation": user_explanation,
        "diagnosed_issue": issue,
        "confidence": confidence,
        "coach_advice": tip,
        "self_corrected": False
    }

    blob_name = f"{user_id}/{int(time.time())}.json"
    upload_json_to_blob(
        storage,
        COACH_CONTAINER,
        blob_name,
        coach_event
    )

    st.success("Coaching feedback saved. Keep going 💪")
