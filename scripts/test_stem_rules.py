"""
scripts/test_stem_rules.py

Quick regression test for stem-based subtype detection.
Usage:
  python -m scripts.test_stem_rules
"""

from services.subtype_classifier import detect_subtype_from_stem

CASES = [
    ("Which one of the following, if true, most strengthens the argument?", "Strengthen"),
    ("Each of the following, if true, strengthens the argument, EXCEPT:", "Strengthen"),
    ("Which one of the following, if true, most weakens the argument?", "Weaken"),
    ("Each of the following, if true, weakens the argument, EXCEPT:", "Weaken"),
    ("If the statements above are true, which of the following must be true?", "Inference (Must Be True)"),
    ("Which one of the following cannot be true?", "Cannot Be True"),
    ("Which one of the following is most strongly supported by the information above?", "Most Strongly Supported"),
    ("The argument depends on which one of the following assumptions?", "Necessary Assumption"),
    ("Which one of the following, if assumed, allows the conclusion to be properly drawn?", "Sufficient Assumption"),
    ("The reasoning in the argument is flawed because it:", "Flaw"),
]

def main():
    failed = 0
    for stem, expected in CASES:
        got = detect_subtype_from_stem(stem)
        if got != expected:
            failed += 1
            print(f"❌ FAIL\n  stem: {stem}\n  expected: {expected}\n  got: {got}\n")
        else:
            print(f"✅ PASS  {expected}  |  {stem}")

    if failed:
        raise SystemExit(f"\n{failed} stem tests failed.")
    print("\nAll stem tests passed.")

if __name__ == "__main__":
    main()
