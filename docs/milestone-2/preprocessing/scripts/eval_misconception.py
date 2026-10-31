"""Score the dynamic misconception detector (backend/app/services/misconception.py).

Two checks:
  1. the 32 hand-written scenarios in test_scenarios/misconceptions.jsonl;
  2. a held-out set built here from the same error types with NEW numbers, to show the detector computes
     its candidates from the question and does not remember the 32 items.
For each item: `detected` = a diagnosis was returned; `exact` = its name equals the label.

Usage: python docs/milestone-2/preprocessing/scripts/eval_misconception.py
"""
import json
import sys
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[2] / "backend"))
from app.services import misconception  # noqa: E402


def fmt(v: F) -> str:
    return str(v.numerator) if v.denominator == 1 else str(v)


def held_out():
    """(question, correct, wrong, label) with numbers that are not in the scenario file."""
    items = []
    for p, n in [(30, 70), (12, 150), (45, 200), (35, 40)]:
        items += [(f"What is {p}% of {n}?", fmt(F(p * n, 100)), fmt(F(n, p)), "divides_by_the_percent"),
                  (f"What is {p}% of {n}?", fmt(F(p * n, 100)), fmt(F(p * n)), "forgets_to_divide_by_100")]
    for a, b, c, d in [(1, 3, 1, 4), (2, 5, 1, 2), (3, 4, 1, 8)]:
        right = F(a, b) + F(c, d)
        items.append((f"What is {a}/{b} + {c}/{d}?", fmt(right), fmt(F(a + c, b + d)), "adds_tops_and_bottoms"))
    for a, b, n in [(1, 8, 64), (1, 3, 27), (2, 5, 30)]:
        items.append((f"What is {a}/{b} of {n}?", fmt(F(a * n, b)), fmt(F(n * b)), "multiplies_by_the_denominator"))
    for a, b in [(4, 9), (2, 11), (7, 12)]:
        items.append((f"What is {a} - {b}?", str(a - b), str(abs(a - b)), "ignores_the_sign"))
    for a, b, c in [(3, 5, 17), (4, 6, 38), (2, 9, 31)]:
        items.append((f"Solve {a}x + {b} = {c}.", fmt(F(c - b, a)), str(c - b), "forgets_to_divide"))
    for c, x, k in [(5, 6, 3), (4, 7, 1), (2, 5, 8)]:
        items.append((f"If x = {x}, what is {c}x - {k}?", str(c * x - k), str(int(f"{c}{x}") - k), f"reads_{c}x_as_digits"))
    for dist, t in [(150, 3), (90, 6), (200, 8)]:
        items.append((f"A bus covers {dist} km in {t} hours. What is its speed in km/h?", fmt(F(dist, t)), str(dist * t),
                      "multiplies_instead_of_dividing"))
    for f, d in [(15, 3), (8, 4), (12, 6)]:
        items.append((f"How much work does a {f} N force do in moving an object {d} m in its own direction (in joules)?",
                      str(f * d), fmt(F(f, d)), "divides_instead_of_multiplying"))
    for n1, cost, n2 in [(4, 20, 9), (2, 14, 5)]:
        items.append((f"If {n1} pens cost {cost} rupees, what do {n2} pens cost?", str(cost * n2 // n1), str(cost + n2 - n1),
                      "additive_instead_of_multiplicative"))
    return items


def score(items):
    detected = exact = 0
    misses = []
    for q, ok, bad, label in items:
        misconception.reset_history()
        d = misconception.diagnose(q, bad, ok)
        detected += d is not None
        exact += bool(d and d.name == label)
        if not (d and d.name == label):
            misses.append((q, bad, label, d.name if d else None))
    return {"items": len(items), "detected": detected, "exact_name": exact}, misses


if __name__ == "__main__":
    scen = [json.loads(line) for line in open(ROOT / "test_scenarios" / "misconceptions.jsonl", encoding="utf8")]
    results = {}
    for name, items in (("scenarios", [(s["question"], s["correct_answer"], s["wrong_answer"], s["misconception"]) for s in scen]),
                        ("held_out_new_numbers", held_out())):
        results[name], misses = score(items)
        print(name, results[name])
        for m in misses:
            print("   miss:", m)
    # a correct answer must not be flagged
    misconception.reset_history()
    assert misconception.diagnose("What is 20% of 50?", "10", "10") is None
    # history: a repeated error becomes recurring and more confident
    misconception.reset_history()
    first = misconception.diagnose("What is 20% of 50?", "2.5", "10", "kid")
    again = misconception.diagnose("What is 15% of 60?", "4", "9", "kid")
    print("history:", first.confidence, "->", again.confidence, "recurring", again.recurring)
    (ROOT / "processed").mkdir(exist_ok=True)
    (ROOT / "processed" / "misconception_eval.json").write_text(json.dumps(results, indent=2))
