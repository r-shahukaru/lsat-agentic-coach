"""
services/tutor_agent.py

Guided practice tutor agent.
Asks probing questions, analyzes reasoning, and responds supportively.
"""

from __future__ import annotations
import os
import requests
from typing import Dict, Any, List


def _azure_chat(messages: List[Dict[str, str]], max_tokens: int = 700) -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT").rstrip("/")
    key = os.getenv("AZURE_OPENAI_API_KEY")
    dep = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    ver = os.getenv("AZURE_OPENAI_API_VERSION")

    url = f"{endpoint}/openai/deployments/{dep}/chat/completions?api-version={ver}"
    headers = {"Content-Type": "application/json", "api-key": key}

    payload = {
        "messages": messages,
        "max_completion_tokens": max_tokens,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def tutor_feedback(
    question: str,
    options: Dict[str, str],
    subtype: str,
    chosen_option: str,
    student_reasoning: str,
) -> Dict[str, Any]:
    """
    Returns structured tutor feedback.
    """

    system = (
        "You are a supportive LSAT tutor.\n"
        "Tone: encouraging, calm, confident.\n"
        "Goals:\n"
        "- Identify reasoning gaps, not just correctness\n"
        "- Explain logic clearly\n"
        "- Tailor advice to the given question subtype\n"
        "Never shame the student.\n\n"
        "Return ONLY JSON:\n"
        "{\n"
        '  "diagnosis": "<what went wrong or right>",\n'
        '  "core_mistake": "<named mistake or None>",\n'
        '  "feedback": "<encouraging explanation>",\n'
        '  "advice": "<how to approach this subtype next time>"\n'
        "}"
    )

    user = (
        f"Question:\n{question}\n\n"
        f"Subtype:\n{subtype}\n\n"
        f"Options:\n{options}\n\n"
        f"Student chose: {chosen_option}\n\n"
        f"Student reasoning:\n{student_reasoning}\n\n"
        "Analyze the reasoning and respond."
    )

    raw = _azure_chat(
        [{"role": "system", "content": system},
        {"role": "user", "content": user}],
        max_completion_tokens=700,
    )


    import json, re
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(match.group(0))
