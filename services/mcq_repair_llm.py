"""
services/mcq_repair_llm.py

LLM fallback for repairing LSAT MCQ structure when OCR breaks option labels.
This is ONLY for structure (question + A–E options). Not for solving.
"""

from __future__ import annotations

import os
import json
import re
import requests
from typing import Dict, Any, Union
from dotenv import load_dotenv


def _azure_chat(messages, max_completion_tokens: int = 900) -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    key = os.getenv("AZURE_OPENAI_API_KEY", "")
    dep = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
    ver = os.getenv("AZURE_OPENAI_API_VERSION", "").strip().split()[0]
    ver = ver.split("/")[0]

    if not all([endpoint, key, dep, ver]):
        raise RuntimeError("Missing Azure OpenAI env vars (endpoint/key/deployment/api_version)")

    url = f"{endpoint}/openai/deployments/{dep}/chat/completions?api-version={ver}"
    headers = {"Content-Type": "application/json", "api-key": key}

    # This deployment does NOT support temperature or max_tokens.
    payload = {
        "messages": messages,
        "max_completion_tokens": max_completion_tokens,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Azure OpenAI error {resp.status_code}: {resp.text}")

    content = resp.json()["choices"][0]["message"].get("content", "")
    return content or ""


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Accepts either:
    - pure JSON response
    - JSON embedded in extra text
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty LLM output")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object found in LLM output")

    return json.loads(m.group(0))


RepairResult = Union[
    Dict[str, str],  # {"status": "NEEDS_REVIEW"}
    Dict[str, Any],  # {"question": "...", "options": {...}}
]


def repair_question_and_options(question_block: str) -> RepairResult:
    """
    Attempts to reconstruct (question + options A–E) from OCR text.
    Returns either:
      - {"question": "...", "options": {...}}
      - {"status": "NEEDS_REVIEW"}
    """
    load_dotenv()

    system = (
        "You are repairing OCR-damaged LSAT multiple-choice questions.\n"
        "Your job is ONLY to reconstruct option labels and option text.\n\n"
        "STRICT RULES:\n"
        "- Output MUST be valid JSON\n"
        "- Options MUST be labeled A, B, C, D, E\n"
        "- Each option value MUST be non-empty text\n"
        "- If ANY option text is missing or unclear, return exactly:\n"
        '  { "status": "NEEDS_REVIEW" }\n\n'
        "Do NOT invent content.\n"
        "Do NOT merge the question stem into options.\n"
        "Do NOT omit option A.\n\n"
        "Return ONE of the following formats ONLY:\n"
        '1) { "question": "...", "options": { "A": "...", "B": "...", "C": "...", "D": "...", "E": "..." } }\n'
        '2) { "status": "NEEDS_REVIEW" }'
    )

    user = f"OCR QUESTION BLOCK:\n{question_block}"

    raw = _azure_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_completion_tokens=900,
    )

    # If model returns nothing, fail safely
    try:
        data = _extract_json(raw)
    except ValueError:
        return {"status": "NEEDS_REVIEW"}



    # If model explicitly says needs review, honor it
    if isinstance(data, dict) and data.get("status") == "NEEDS_REVIEW":
        return {"status": "NEEDS_REVIEW"}

    if not isinstance(data, dict):
        return {"status": "NEEDS_REVIEW"}

    q = (data.get("question") or "").strip()
    opts = data.get("options")

    if not q:
        return {"status": "NEEDS_REVIEW"}

    if not isinstance(opts, dict):
        return {"status": "NEEDS_REVIEW"}

    # Hard guardrails: must have all A–E non-empty
    cleaned: Dict[str, str] = {}
    for k in ["A", "B", "C", "D", "E"]:
        v = (opts.get(k) or "").strip()
        if not v:
            return {"status": "NEEDS_REVIEW"}
        cleaned[k] = v

    return {"question": q, "options": cleaned}
