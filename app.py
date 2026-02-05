import streamlit as st
from pathlib import Path

# Render the same Home page content
home_path = Path("app/Home.py")

# Run Home.py in this process so multipage still works
code = home_path.read_text(encoding="utf-8")
exec(compile(code, str(home_path), "exec"))
