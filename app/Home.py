import sys
from pathlib import Path
import streamlit as st

# Add project root to path so services/ can be imported
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

st.set_page_config(page_title="LSAT Agentic Coach", layout="wide")

st.title("🎯 LSAT Agentic Coach")

st.markdown("""
Welcome to your local LSAT practice and coaching tool.  
Use the sidebar to navigate between:
- 📝 **Guided Practice** — do real questions
- 🧠 **Tutor Coach** — reflect on your reasoning and get feedback

All data is stored locally in the `data/` folder.  
No cloud setup. No Azure. Just pure focus.
""")
