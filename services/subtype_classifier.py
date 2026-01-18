"""
services/subtype_classifier.py

Classifies LSAT question subtypes using Azure OpenAI with a validator step.

Best practice used:
- Constrained label set
- Strict JSON output
- Second-pass judge validation
- Fail-safe to NeedsReview
"""

from __future__ import annotations

import os
import json
import re
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv
from streamlit import text

def _azure_openai_chat(messages: List[Dict[str, str]]) -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "").strip().split()[0]
    api_version = api_version.split("/")[0]

    if not all([endpoint, api_key, deployment, api_version]):
        raise RuntimeError("Missing Azure OpenAI environment variables")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    # This deployment does NOT support temperature or max_tokens.
    payload = {
        "messages": messages,
        "max_completion_tokens": 1200,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)

    if resp.status_code >= 400:
        raise RuntimeError(f"Azure OpenAI error {resp.status_code}: {resp.text}")

    data = resp.json()
    content = ((data.get("choices") or [{}])[0].get("message", {}) or {}).get("content", "")

    # One retry if Azure returns empty content
    if not content or not content.strip():
        resp2 = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp2.status_code >= 400:
            raise RuntimeError(f"Azure OpenAI error {resp2.status_code}: {resp2.text}")
        data2 = resp2.json()
        content2 = ((data2.get("choices") or [{}])[0].get("message", {}) or {}).get("content", "")
        if not content2 or not content2.strip():
            raise RuntimeError(
                "Empty model content after retry. "
                f"First response: {json.dumps(data, ensure_ascii=False)[:1500]} | "
                f"Second response: {json.dumps(data2, ensure_ascii=False)[:1500]}"
            )
        return content2

    return content


def detect_subtype_from_stem(question: str) -> str | None:
    """
    Cheap deterministic stem detector.
    Returns a subtype label (must be in SUBTYPE_LABELS) or None.
    """
    q = " ".join(question.lower().split())  # normalize whitespace

    def has(*phrases: str) -> bool:
        return any(p in q for p in phrases)

    # --- Strengthen / Weaken (including EXCEPT forms) ---
    if has("strengthen") and has("except"):
        return "Strengthen"
    if has("weaken") and has("except"):
        return "Weaken"

    # common strengthen stems
    if has("most strengthens", "most strongly supports the argument", "provides the strongest support", "strengthens the argument"):
        return "Strengthen"

    # common weaken stems
    if has("most weakens", "most seriously weakens", "undermines the argument", "weakens the argument", "calls into question"):
        return "Weaken"

    # --- Inference family ---
    if has("cannot be true", "could not be true"):
        return "Cannot Be True"
    if has("must be true", "must also be true", "which of the following is most strongly supported by"):
        # note: "most strongly supported" is separate below; this catches must-be-true style
        return "Inference (Must Be True)"
    if has("most strongly supported"):
        return "Most Strongly Supported"

    # --- Assumptions ---
    # Sufficient Assumption stems often say "if assumed" but may not include the word "assumption".
    if has(
        "if assumed",
        "if we assume",
        "allows the conclusion to be properly drawn",
        "enables the conclusion",
        "sufficient to justify",
        "properly drawn",
    ):
        return "Sufficient Assumption"

    # Necessary Assumption usually explicitly uses "assumption/depends/relies/required"
    if has("assumption", "assumes", "required assumption", "depends on the assumption", "relies on the assumption"):
        return "Necessary Assumption"

    # --- Flaw / Method / Role / Conclusion ---
    if has("flaw", "reasoning is flawed", "questionable reasoning", "error in the argument"):
        return "Flaw"
    if has("method of reasoning", "reasoning proceeds by", "argument does which one of the following"):
        return "Method of Reasoning"
    if has("role", "plays which one of the following roles", "function of the statement"):
        return "Role of Statement"
    if has("main conclusion", "conclusion of the argument", "the argument's conclusion"):
        return "Main Conclusion"

    # --- Evaluate / Resolve ---
    if has("evaluate", "would be most useful to know", "would be most helpful to determine"):
        return "Evaluate"
    if has("resolve", "reconcile", "explain the discrepancy", "help to explain", "apparent contradiction", "paradox"):
        return "Resolve/Reconcile"

    # --- Principle / Parallel ---
    if has("principle") and has("justify"):
        return "Principle (Justify)"
    if has("principle"):
        return "Principle (Conform)"
    if has("parallel flaw"):
        return "Parallel Flaw"
    if has("parallel reasoning", "most closely parallels"):
        return "Parallel Reasoning"

    return None



# A solid baseline LSAT LR taxonomy. You can edit/extend this any time.
SUBTYPE_LABELS: List[str] = [
    "Strengthen",
    "Weaken",
    "Flaw",
    "Necessary Assumption",
    "Sufficient Assumption",
    "Inference (Must Be True)",
    "Most Strongly Supporte",
    "Cannot Be True",
    "Main Conclusion",
    "Method of Reasoning",
    "Role of Statement",
    "Resolve/Reconcile (Paradox)",
    "Evaluate",
    "Principle (Justify)",
    "Principle (Conform) (aka Identify/Match)",
    "Parallel Reasoning",
    "Parallel Flaw",
]

NEEDS_REVIEW = "NeedsReview"

def _extract_json(text: str) -> dict:
    """
    Extracts a JSON object from model output.

    Strategy:
    1) First try parsing the entire response as JSON
    2) If that fails, fall back to extracting the first {...} block
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Model returned empty output (no JSON to parse).")

    # 1) Fast path: model returned pure JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) Fallback: extract JSON block from surrounding text
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError(f"Could not find JSON in model output: {text}")

    try:
        return json.loads(m.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON extracted from model output: {e}\n{text}")


def classify_subtype_primary(question: str, options: Dict[str, str]) -> Dict[str, Any]:

    user = (
        f"Question:\n{question}\n\n"
        f"Options:\n{json.dumps(options, ensure_ascii=False, indent=2)}\n"
        "Labels: Strengthen, Weaken, Flaw, Inference, ..."
    )

    """Primary classification call returning subtype + confidence + rationale."""
    labels = ", ".join(SUBTYPE_LABELS)

    system = (
        "You are an LSAT Logical Reasoning question classifier.\n"
        "You must choose exactly ONE subtype label from the allowed list.\n"
        "Return ONLY valid JSON in the schema:\n"
        '{ "subtype": "<label>", "confidence": 0.0-1.0, "rationale": "<one short sentence>" }\n'
        "No extra keys. No extra text."
    )

    user = (
        f"Allowed labels:\n{labels}\n\n"
        f"Question:\n{question}\n\n"
        f"Options:\n{json.dumps(options, ensure_ascii=False, indent=2)}\n\n"
        "Classify the subtype."
    )

    raw = _azure_openai_chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    data = _extract_json(raw)

    # Validating label constraint.
    if data.get("subtype") not in SUBTYPE_LABELS:
        return {"subtype": NEEDS_REVIEW, "confidence": 0.0, "rationale": "Invalid label from model."}

    # Clamping confidence.
    try:
        conf = float(data.get("confidence", 0.0))
    except Exception:
        conf = 0.0

    data["confidence"] = max(0.0, min(1.0, conf))
    return data


def validate_subtype_judge(question: str, options: Dict[str, str], proposed: str) -> Dict[str, Any]:
    """Judge call that approves/rejects proposed subtype and suggests correction."""
    labels = ", ".join(SUBTYPE_LABELS)

    system = (
        "You are a strict LSAT Logical Reasoning subtype validator.\n"
        "You must validate whether the proposed subtype matches the QUESTION STEM.\n"
        "IMPORTANT:\n"
        "- If the stem says 'strengthens ... EXCEPT', the subtype is still Strengthen.\n"
        "- If the stem says 'weakens ... EXCEPT', the subtype is still Weaken.\n"
        "Return ONLY valid JSON:\n"
        '{ "verdict": "approve" or "reject", "correct_subtype": "<label>", "reason": "<short>" }\n'
        "correct_subtype MUST be one allowed label."
    )

    user = (
        f"Allowed labels:\n{labels}\n\n"
        f"Proposed subtype: {proposed}\n\n"
        f"Question:\n{question}\n\n"
        f"Options:\n{json.dumps(options, ensure_ascii=False, indent=2)}\n\n"
        "Decide approve/reject and give the correct label."
    )

    raw = _azure_openai_chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    data = _extract_json(raw)

    verdict = data.get("verdict", "").lower()
    correct = data.get("correct_subtype")

    if correct not in SUBTYPE_LABELS:
        return {"verdict": "reject", "correct_subtype": NEEDS_REVIEW, "reason": "Judge returned invalid label."}

    if verdict not in ["approve", "reject"]:
        verdict = "reject"

    return {"verdict": verdict, "correct_subtype": correct, "reason": "<≤12 words> Keep 'reason' extremely short."}


def classify_subtype_with_guardrails(question: str, options: Dict[str, str]) -> Dict[str, Any]:
    """
    Full best-practice flow:
    - primary classify
    - judge validate
    - repair once if rejected or low confidence
    """

    # Hard rule: stem-based detection overrides model (prevents obvious subtype failures)
    stem_label = detect_subtype_from_stem(question)
    if stem_label is not None and stem_label in SUBTYPE_LABELS:
        return {
            "subtype": stem_label,
            "confidence": 0.95,
            "rationale": "Detected from question stem keywords (deterministic rule).",
            "judge_verdict": "approve",
            "judge_reason": "Stem rule override.",
        }


    primary = classify_subtype_primary(question, options)
    proposed = primary["subtype"]

    # If primary already failed constraints, returning NeedsReview.
    if proposed == NEEDS_REVIEW:
        return {**primary, "judge_verdict": "reject", "judge_reason": "Primary invalid."}

    judge = validate_subtype_judge(question, options, proposed)

    # Approving if judge approves and confidence is decent.
    if judge["verdict"] == "approve" and primary["confidence"] >= 0.60:
        return {
            "subtype": proposed,
            "confidence": primary["confidence"],
            "rationale": primary["rationale"],
            "judge_verdict": "approve",
            "judge_reason": judge["reason"],
        }

    # Repair attempt: force the model to reconsider using judge feedback.
    repair_system = (
        "You are an LSAT subtype classifier.\n"
        "You must output ONLY valid JSON:\n"
        '{ "subtype": "<label>", "confidence": 0.0-1.0, "rationale": "<one short sentence>" }\n'
        "Choose one label from the allowed list."
    )
    repair_user = (
        f"Allowed labels:\n{', '.join(SUBTYPE_LABELS)}\n\n"
        f"Question:\n{question}\n\n"
        f"Options:\n{json.dumps(options, ensure_ascii=False, indent=2)}\n\n"
        f"Previous proposed subtype: {proposed}\n"
        f"Judge suggested subtype: {judge['correct_subtype']}\n"
        f"Judge reason: {judge['reason']}\n\n"
        "Return the best subtype label."
    )

    raw = _azure_openai_chat([{"role": "system", "content": repair_system}, {"role": "user", "content": repair_user}])
    repaired = _extract_json(raw)

    if repaired.get("subtype") not in SUBTYPE_LABELS:
        return {
            "subtype": NEEDS_REVIEW,
            "confidence": 0.0,
            "rationale": "Repair produced invalid label.",
            "judge_verdict": "reject",
            "judge_reason": judge["reason"],
        }

    try:
        conf = float(repaired.get("confidence", 0.0))
    except Exception:
        conf = 0.0

    conf = max(0.0, min(1.0, conf))

    # Final: accept judge's suggested subtype if repaired confidence is still weak.
    final_subtype = repaired["subtype"] if conf >= 0.55 else judge["correct_subtype"]

    return {
        "subtype": final_subtype,
        "confidence": conf,
        "rationale": repaired.get("rationale", ""),
        "judge_verdict": judge["verdict"],
        "judge_reason": judge["reason"],
    }
