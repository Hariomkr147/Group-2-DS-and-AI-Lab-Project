"""Dynamic misconception detector.

Given a question, the learner's wrong answer and the correct answer, find the error that explains the wrong
answer. Nothing is looked up by question: every call rebuilds the candidate wrong answers from the numbers in
the question, in two ways, and keeps the candidate that reproduces the learner's answer.

1. Error patterns. A small library of known error procedures (divide by the percent instead of taking the
   percent of, add tops and bottoms of fractions, ...). Each one fires only when the question has the shape it
   needs, and computes its wrong answer from that question's own numbers.
2. Search. For questions no pattern covers, try every expression of up to three of the question's numbers
   (+ - x /) and keep those that equal the learner's answer. If the correct answer is also one such expression,
   the error is named by comparing the two ("multiplies instead of dividing").

It adapts to the learner: an error seen before for the same learner is preferred when two explanations tie, and
its confidence rises. No match returns None, so the tutor falls back to a generic hint.
"""
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import product

NUM = r"-?\d+(?:\.\d+)?"
_VERB = {"+": "adds", "-": "subtracts", "*": "multiplies", "/": "divides"}
_GERUND = {"+": "adding", "-": "subtracting", "*": "multiplying", "/": "dividing"}
_SYMBOL = {"+": "+", "-": "-", "*": "x", "/": "÷"}

_seen: dict[str, Counter] = defaultdict(Counter)  # learner id -> how often each error was diagnosed


@dataclass
class Diagnosis:
    name: str
    explanation: str
    confidence: float
    source: str            # "pattern" or "search"
    recurring: bool = False


def to_value(text: str) -> F | None:
    t = text.strip().replace(",", "").replace(" ", "").rstrip(".")
    try:
        return F(t[:-1]) / 100 if t.endswith("%") else F(t)
    except (ValueError, ZeroDivisionError):
        return None


def _show(v: F) -> str:
    return str(v.numerator) if v.denominator == 1 else (
        str(float(v)) if v.denominator in (2, 4, 5, 8, 10, 20, 25, 50, 100) else str(v))


# ---------------------------------------------------------------- 1. error patterns
# Each pattern returns [(name, wrong_value, explanation)] for questions of its shape, else [].
def _percent_of(q):
    m = re.search(rf"({NUM})\s*%\s*of\s*({NUM})", q)
    if not m:
        return []
    p, n = F(m[1]), F(m[2])
    return [("divides_by_the_percent", n / p if p else None, f"divided {n} by {p} instead of finding {p}/100 of {n}"),
            ("forgets_to_divide_by_100", p * n, f"multiplied {p} by {n} and did not divide by 100"),
            ("percent_decimal_shift", p * n / 10, "moved the decimal point one place instead of two"),
            ("adds_the_percent", n + p, f"added {p} to {n}")]


def _percent_as_decimal(q):
    m = re.search(rf"({NUM})\s*%\s*as\s*a\s*(?:decimal|fraction)", q)
    if not m:
        return []
    p = F(m[1])
    return [("percent_decimal_shift", p / 10, "moved the decimal point one place instead of two"),
            ("forgets_to_convert_percent", p, "wrote the percent number without converting it"),
            ("shifts_decimal_too_far", p / 1000, "moved the decimal point three places")]


def _fraction_add(q):
    m = re.search(r"(\d+)/(\d+)\s*\+\s*(\d+)/(\d+)", q)
    if not m:
        return []
    a, b, c, d = map(int, m.groups())
    return [("adds_tops_and_bottoms", F(a + c, b + d), f"added the tops ({a}+{c}) and the bottoms ({b}+{d})"),
            ("multiplies_instead_of_adding", F(a * c, b * d), "multiplied the fractions instead of adding them")]


def _fraction_of(q):
    m = re.search(rf"(\d+)/(\d+)\s+of\s+({NUM})", q)
    if not m:
        return []
    a, b, n = int(m[1]), int(m[2]), F(m[3])
    return [("multiplies_by_the_denominator", n * b, f"multiplied {n} by the denominator {b}"),
            ("divides_by_the_numerator", n / a, f"divided {n} by the numerator {a}")]


def _fraction_divide(q):
    m = re.search(r"(\d+(?:/\d+)?)\s+divided by\s+(\d+)/(\d+)", q)
    if not m:
        return []
    top, c, d = F(m[1]), int(m[2]), int(m[3])
    name = "multiplies_instead_of_dividing" if "/" in m[1] else "forgets_the_reciprocal"
    return [(name, top * F(c, d), "multiplied by the second fraction without flipping it")]


def _compare(q):
    m = re.search(rf"which is (larger|greater|bigger|smaller|less|lesser)[,:]?\s*({NUM}(?:/\d+)?)\s+or\s+({NUM}(?:/\d+)?)", q)
    if not m:
        return []
    want_big = m[1] in ("larger", "greater", "bigger")
    texts = [m[2], m[3]]
    values = [F(t) for t in texts]
    hypotheses = []
    if all("/" in t for t in texts):
        hypotheses.append(("compares_numerators_only", [int(t.split("/")[0]) for t in texts]))
    if all("." in t and not t.startswith("-") for t in texts):
        hypotheses.append(("longer_decimal_is_bigger", [int(t.split(".")[1]) for t in texts]))
    if all(v < 0 for v in values):
        hypotheses.append(("bigger_digit_bigger_number", [abs(v) for v in values]))
    out = []
    for name, keys in hypotheses:
        if keys[0] != keys[1]:
            pick = keys.index(max(keys) if want_big else min(keys))
            out.append((name, values[pick], "compared the wrong feature of the two numbers"))
    return out


def _integer_arithmetic(q):
    m = re.search(rf"^(?:what is|evaluate|find)\s+({NUM})\s*([+\-])\s*({NUM})\s*\??$", q.strip())
    if not m:
        return []
    a, op, b = F(m[1]), m[2], F(m[3])
    out = []
    if op == "-":
        out += [("ignores_the_sign", abs(a - b), "gave the size of the difference and dropped its sign"),
                ("treats_minus_as_plus", a + b, "added instead of subtracting")]
    else:
        if (a < 0) != (b < 0):
            out.append(("adds_magnitudes_keeps_negative", -(abs(a) + abs(b)), "added the sizes and kept a minus sign"))
        out.append(("treats_plus_as_minus", a - b, "subtracted instead of adding"))
    return out


def _decimal_add(q):
    m = re.search(r"(\d*)\.(\d+)\s*\+\s*(\d*)\.(\d+)", q)
    if not m:
        return []
    total = int(m[2]) + int(m[4])
    return [("misaligned_decimal_places", F(total, 10 ** len(str(total))),
             "added the digits after the point as whole numbers without lining up the places")]


def _linear_equation(q):
    s = q.replace(" ", "")
    m = re.search(rf"(\d*)x([+-])(\d+)=({NUM})", s)
    if m:
        a, sign, b, c = int(m[1] or 1), (1 if m[2] == "+" else -1), int(m[3]), F(m[4])
        if a != 1:
            return [("forgets_to_divide", c - sign * b, f"moved the {b} but did not divide by {a}"),
                    ("sign_error_moving_a_term", (c + sign * b) / a, f"kept the sign of {b} when moving it across")]
        return [("adds_instead_of_subtracting" if sign == 1 else "subtracts_instead_of_adding", c + sign * b,
                 "did the same operation as the equation instead of undoing it")]
    m = re.search(rf"(\d+)\(x([+-])(\d+)\)=({NUM})", s)
    if m:
        a, sign, b, c = int(m[1]), (1 if m[2] == "+" else -1), int(m[3]), F(m[4])
        return [("distributes_to_first_term_only", (c - sign * b) / a, f"multiplied only x by {a}, not the {b}")]
    return []


def _substitution(q):
    m = re.search(rf"if ([a-z])\s*=\s*({NUM}).*?(\d+)\1\s*([+-])\s*(\d+)", q)
    if not m:
        return []
    var, val, coef, op, const = m[1], m[2], m[3], m[4], F(m[5])
    glued = F(coef + val)
    return [(f"reads_{coef}{var}_as_digits", glued + const if op == "+" else glued - const,
             f"read {coef}{var} as the digits {coef} and {val} side by side ({coef}{val})")]


def _ratio_share(q):
    m = re.search(rf"divide ({NUM}) in the ratio (\d+)\s*:\s*(\d+)", q)
    if not m:
        return []
    total, a, b = F(m[1]), int(m[2]), int(m[3])
    small, big = total * min(a, b) / (a + b), total * max(a, b) / (a + b)
    return [("splits_equally", total / 2, "split the amount into equal halves, ignoring the ratio"),
            ("picks_the_other_share", small if "larger" in q or "bigger" in q else big, "gave the other share")]


def _proportion(q):
    m = re.search(rf"if ({NUM})\s+\w+\s+cost\s+({NUM})\D+?({NUM})\s+\w+\s+cost", q)
    if not m:
        return []
    n1, cost, n2 = F(m[1]), F(m[2]), F(m[3])
    return [("additive_instead_of_multiplicative", cost + (n2 - n1),
             f"added the {n2 - n1} extra items to the cost instead of scaling the cost")]


def _kinetic_energy(q):
    m = re.search(rf"({NUM})\s*kg.*?({NUM})\s*m/s", q)
    if not m or "kinetic" not in q:
        return []
    mass, speed = F(m[1]), F(m[2])
    return [("forgets_to_square_speed", mass * speed / 2, "used the speed, not the speed squared"),
            ("doubles_instead_of_squaring", mass * 2 * speed / 2, "doubled the speed instead of squaring it")]


PATTERNS = [_percent_of, _percent_as_decimal, _fraction_add, _fraction_of, _fraction_divide, _compare,
            _integer_arithmetic, _decimal_add, _linear_equation, _substitution, _ratio_share, _proportion,
            _kinetic_energy]


# ---------------------------------------------------------------- 2. search over expressions
def _apply(op: str, x: F, y: F) -> F | None:
    if op == "/":
        return x / y if y else None
    return {"+": x + y, "-": x - y, "*": x * y}[op]


def _expressions(numbers: list[F]):
    """All expressions of 2-3 of the numbers: (value, tree). A tree is a number or (op, left, right)."""
    level1 = [(n, n) for n in numbers]
    level2 = []
    for (va, ta), (vb, tb) in product(level1, repeat=2):
        for op in "+-*/":
            value = _apply(op, va, vb)
            if value is not None:
                level2.append((value, (op, ta, tb)))
    level3 = []
    for (v2, t2), (v1, t1) in product(level2, level1):
        for op in "+-*/":
            for (x, tx), (y, ty) in (((v2, t2), (v1, t1)), ((v1, t1), (v2, t2))):
                value = _apply(op, x, y)
                if value is not None:
                    level3.append((value, (op, tx, ty)))
    return level2 + level3


def _leaves(tree) -> list:
    return [tree] if not isinstance(tree, tuple) else _leaves(tree[1]) + _leaves(tree[2])


def _depth(tree) -> int:
    return 0 if not isinstance(tree, tuple) else 1 + max(_depth(tree[1]), _depth(tree[2]))


def _render(tree, top: bool = True) -> str:
    if not isinstance(tree, tuple):
        return _show(tree)
    text = f"{_render(tree[1], False)} {_SYMBOL[tree[0]]} {_render(tree[2], False)}"
    return text if top else f"({text})"


def _search(question: str, learner: F, correct: F | None) -> list[tuple[str, str]]:
    # a number may be used as often as it appears in the question ("m/s^2" must not add a 2)
    available = Counter(F(x) for x in re.findall(NUM, re.sub(r"\^\d", "", question)))
    numbers = list(available)[:5]
    if not numbers:
        return []
    exprs = [(v, t) for v, t in _expressions(numbers) if not Counter(_leaves(t)) - available]
    exprs.sort(key=lambda e: (_depth(e[1]), len(_leaves(e[1]))))
    wrong = [t for v, t in exprs if v == learner]
    right = [t for v, t in exprs if correct is not None and v == correct]
    out = []
    for w in wrong[:40]:
        intended = next((r for r in right if sorted(_leaves(r)) == sorted(_leaves(w)) and _depth(r) == _depth(w)), None)
        name = "uses_a_wrong_expression"
        if intended and _depth(w) == 1 and intended[0] != w[0]:
            name = f"{_VERB[w[0]]}_instead_of_{_GERUND[intended[0]]}"
        elif intended and _depth(w) == 2 and intended[0] == w[0] and intended != w:
            diff = next(((a[0], b[0]) for a, b in ((w[1], intended[1]), (w[2], intended[2]))
                         if isinstance(a, tuple) and isinstance(b, tuple) and a[0] != b[0]), None)
            if diff:
                name = f"{_VERB[diff[0]]}_instead_of_{_GERUND[diff[1]]}"
        out.append((name, f"your answer equals {_render(w)}"))
    out.sort(key=lambda o: o[0] == "uses_a_wrong_expression")   # explanations that name the error come first
    return out[:6]


# ---------------------------------------------------------------- public API
def diagnose(question: str, learner_answer: str, correct_answer: str, learner_id: str | None = None) -> Diagnosis | None:
    learner, correct = to_value(learner_answer), to_value(correct_answer)
    if learner is None or learner == correct:
        return None
    q = question.lower()

    matches = []                      # (name, explanation, source)
    for pattern in PATTERNS:
        for name, value, why in pattern(q):
            if value is not None and F(value) == learner:
                matches.append((name, why, "pattern"))
    if not matches:
        matches = [(n, w, "search") for n, w in _search(question, learner, correct)]
    if not matches:
        return None

    history = _seen[learner_id] if learner_id else Counter()
    best = max(matches, key=lambda m: history[m[0]])    # ties keep the first (simplest) explanation
    names = {m[0] for m in matches}
    base = (0.9 if len(names) == 1 else 0.7) if best[2] == "pattern" else (0.5 if len(names) == 1 else 0.35)
    recurring = history[best[0]] > 0
    confidence = min(0.99, base + 0.1 * min(history[best[0]], 3))
    if learner_id:
        _seen[learner_id][best[0]] += 1
    return Diagnosis(best[0], best[1], round(confidence, 2), best[2], recurring)


def detect(question: str, learner_answer: str, correct_answer: str, learner_id: str | None = None) -> str | None:
    d = diagnose(question, learner_answer, correct_answer, learner_id)
    return d.name if d else None


def reset_history(learner_id: str | None = None) -> None:
    if learner_id:
        _seen.pop(learner_id, None)
    else:
        _seen.clear()
