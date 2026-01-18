"""
Quick test for tutor agent.
"""

from services.tutor_agent import tutor_feedback

question = "A student has taken twelve courses..."
options = {
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "...",
    "E": "..."
}
subtype = "Strengthen"
chosen = "A"
reasoning = "Option A gives more help so it strengthens the argument."

out = tutor_feedback(
    question=question,
    options=options,
    subtype=subtype,
    chosen_option=chosen,
    student_reasoning=reasoning,
)

print(out)
