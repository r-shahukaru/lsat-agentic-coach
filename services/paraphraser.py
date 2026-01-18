"""
services/paraphraser.py

Light paraphrase for LSAT-style questions/options WITHOUT changing meaning.

Best practices:
- Keep original text in JSON
- Produce paraphrase only if meaning is preserved
- Judge/validator rejects unsafe paraphrases
"""

from __future__ import annotations

import json
import re
from typing import Dict, Any, List
import requests
import os


def _azure_openai_chat(messages: List[Dict[str, str]], max_tokens: int = 450) -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "")

    if not all([endpoint, api_key, deployment, api_version]):
        raise RuntimeError("Missing Azure OpenAI env vars (endpoint/key/deployment/api_version)")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    headers = {"Content-Type": "application/json", "api-key": api_key}
    payload = {
        "messages": messages,
        "max_completion_tokens": max_tokens,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _extract_json(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not find JSON in model output: {text}")
    return json.loads(match.group(0))


def paraphrase_light(question: str, options: Dict[str, str]) -> Dict[str, Any]:
    """
    Produces a light paraphrase (small wording changes only).
    Returns:
      { "question": "...", "options": {"A": "...", ...}, "notes": "..." }
    """
    system = (
        "You rewrite LSAT questions with a LIGHT paraphrase.\n"
        "Rules:\n"
        "- Preserve meaning exactly.\n"
        "- Keep logical operators unchanged (if/only if/unless/except).\n"
        "- Do NOT simplify to the point of changing difficulty.\n"
        "- Keep answer choices aligned with original intent.\n"
        "Return ONLY JSON:\n"
        '{ "question": "<paraphrase>", "options": {"A":"...","B":"...","C":"...","D":"...","E":"..."}, "notes":"<one short note>" }'
    )

    user = (
        f"Original question:\n{question}\n\n"
        f"Original options:\n{json.dumps(options, ensure_ascii=False, indent=2)}\n\n"
        "Create a LIGHT paraphrase."
    )

    raw = _azure_openai_chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    return _extract_json(raw)


def judge_paraphrase_safe(original_q: str, original_opts: Dict[str, str], para_q: str, para_opts: Dict[str, str]) -> Dict[str, Any]:
    """
    Judge checks meaning preservation. Approves/rejects.
    """
    system = (
        "You are a strict meaning-preservation judge for LSAT paraphrases.\n"
        "If meaning or logical structure changed, reject.\n"
        "Return ONLY JSON:\n"
        '{ "verdict":"approve" or "reject", "reason":"<short>", "risk":0.0-1.0 }'
    )

    user = (
        f"Original question:\n{original_q}\n\n"
        f"Paraphrased question:\n{para_q}\n\n"
        f"Original options:\n{json.dumps(original_opts, ensure_ascii=False, indent=2)}\n\n"
        f"Paraphrased options:\n{json.dumps(para_opts, ensure_ascii=False, indent=2)}\n\n"
        "Do the paraphrases preserve meaning and logic exactly?"
    )

    raw = _azure_openai_chat([{"role": "system", "content": system}, {"role": "user", "content": user}], max_tokens=200)
    data = _extract_json(raw)

    # Basic normalization
    verdict = str(data.get("verdict", "reject")).lower()
    try:
        risk = float(data.get("risk", 1.0))
    except Exception:
        risk = 1.0

    return {
        "verdict": "approve" if verdict == "approve" else "reject",
        "reason": data.get("reason", ""),
        "risk": max(0.0, min(1.0, risk)),
    }


def paraphrase_with_guardrails(question: str, options: Dict[str, str]) -> Dict[str, Any]:
    """
    Full flow:
    - paraphrase
    - judge validate
    - if reject, return NeedsReview (do not overwrite)
    """
    draft = paraphrase_light(question, options)

    para_q = draft.get("question", "")
    para_opts = draft.get("options", {}) or {}

    judge = judge_paraphrase_safe(question, options, para_q, para_opts)

    if judge["verdict"] != "approve" or judge["risk"] > 0.35:
        return {
            "status": "NeedsReview",
            "judge": judge,
            "paraphrased_question": None,
            "paraphrased_options": None,
        }

    return {
        "status": "OK",
        "judge": judge,
        "paraphrased_question": para_q,
        "paraphrased_options": para_opts,
    }
