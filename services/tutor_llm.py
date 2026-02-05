import os
from openai import OpenAI

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)

def build_tutor_prompt(question: str, options: dict, chosen: str, correct: str, subtype: str, mistake_summary: str) -> tuple[str, str]:
    system = (
        "You are an elite LSAT tutor. You must FIRST explain why the student's chosen answer is wrong, "
        "using the exact wording and logic of that choice. Then explain why the correct answer is right. "
        "Be concrete, not vague. End with a repeatable heuristic for next time. "
        "Do not be motivational; be precise and helpful."
    )

    opts_text = "\n".join([f"{k}) {v}" for k, v in options.items()])

    user = (
        f"Question type: {subtype}\n"
        f"Student mistake patterns (if any): {mistake_summary}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"OPTIONS:\n{opts_text}\n\n"
        f"Student chose: {chosen}\n"
        f"Correct answer: {correct}\n\n"
        "Explain in this structure:\n"
        "1) Why the chosen answer is wrong\n"
        "2) Why the correct answer is right\n"
        "3) Trap pattern / what made it tempting\n"
        "4) Heuristic to avoid this next time\n"
    )
    return system, user

def tutor_response(system, user):
    client = get_client()
    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.output_text

