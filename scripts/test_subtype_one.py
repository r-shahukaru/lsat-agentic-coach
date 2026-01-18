"""
scripts/test_subtype_one.py

Runs subtype classification (with guardrails) on a single hardcoded MCQ.
Usage:
  python -m scripts.test_subtype_one
"""

from typing import List
from dotenv import load_dotenv
from services.subtype_classifier import classify_subtype_with_guardrails

def main():
    load_dotenv(".env")

    question = (
        "A student has taken twelve courses and received a B in a majority of them. "
        "The student is now taking another course and will probably, given her record, "
        "receive a B in it. Each of the following, if true, strengthens the argument, EXCEPT:"
    )

    options = {
        "A": "The student previously studied alone but is receiving help from several outstanding students during the present course.",
        "B": "The twelve courses together covered a broad range of subject matter.",
        "C": "The student previously studied in the library and continues to do so.",
        "D": "The student received a B in all but one of the twelve courses.",
        "E": "The current course is a continuation of one of the twelve courses in which the student received a B.",
    }

    out = classify_subtype_with_guardrails(question, options)
    print(out)

if __name__ == "__main__":
    main()
