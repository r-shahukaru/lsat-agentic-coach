"""app/Home.py

Streamlit entrypoint.

Keeping this file minimal:
- Setting Streamlit page config.
- Ensuring imports work when running `streamlit run app/Home.py`.

Pages live in app/pages/.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st


# Ensuring the repo root is on sys.path so `from services...` works reliably.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    st.set_page_config(
        page_title="LSAT Agentic Coach",
        page_icon="🧠",
        layout="wide",
    )

    st.title("LSAT Agentic Coach")
    st.write(
        "This is the practice app for LSAT MCQs ingested into Azure Blob Storage. "
        "Start with **Guided Practice** from the left sidebar."
    )

    # Showing basic environment hints (non-sensitive).
    with st.expander("Environment (non-sensitive)", expanded=False):
        st.code(
            "\n".join(
                [
                    f"AZURE_CONTAINER_QUESTION_METADATA={os.getenv('AZURE_CONTAINER_QUESTION_METADATA','question-metadata')}",
                    f"AZURE_CONTAINER_USER_PROFILES={os.getenv('AZURE_CONTAINER_USER_PROFILES','user-profiles')}",
                    f"AZURE_CONTAINER_USER_ATTEMPTS={os.getenv('AZURE_CONTAINER_USER_ATTEMPTS','user-attempts')}",
                ]
            )
        )


if __name__ == "__main__":
    main()
