import streamlit as st
import json
from pathlib import Path

st.title("📄 Coach History")

user_id = st.selectbox("User", ["user01"])

events_dir = Path(f"data/user-coach-events/{user_id}")
if not events_dir.exists():
    st.warning("No coaching events found.")
    st.stop()

event_files = sorted(events_dir.glob("*.json"), reverse=True)
if not event_files:
    st.info("No coach sessions recorded yet.")
    st.stop()

event_lookup = {}
for f in event_files:
    with open(f, "r") as file:
        data = json.load(file)
        label = f"{data['timestamp_utc']} – Q: {data['mcq_id']} – {data['diagnosed_issue']}"
        event_lookup[label] = data

choice = st.selectbox("Select a past coaching session:", list(event_lookup.keys()))

selected = event_lookup[choice]

st.subheader(f"Question ID: {selected['mcq_id']}")
st.markdown(f"**Subtype**: `{selected.get('subtype', 'N/A')}`")
st.markdown(f"**Confidence**: {selected.get('confidence', '?')}/5")

st.markdown("### 🧠 Your Explanation")
st.info(selected["user_explanation"])

st.markdown("### 🧪 Coach Diagnosis")
st.warning(selected["diagnosed_issue"])

st.markdown("### 💡 Coach Tip")
st.success(selected["coach_advice"])

if selected.get("self_corrected"):
    st.markdown("✅ You corrected yourself after feedback.")
