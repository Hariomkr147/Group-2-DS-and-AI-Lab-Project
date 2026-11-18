"""Find the first wrong step in a learner's working.

Used only after an answer is graded wrong. Two checks, in this order:

1. Arithmetic, by code. Each line such as "60 / 4 = 16" is recomputed exactly. A line that does not add up is
   a certain error (a slip), so it wins over the model.
2. Method, by our model (STEP_FINDER_PROVIDER, default qwen_finetuned). It gets the question, the correct
   answer and the numbered working, and names the first wrong step in one sentence.

The result is a suggestion for the hint, never a confirmed misconception. No result (None) is normal: the
model is off or unreachable, the reply is unreadable, or nothing was found.
Measured on backend/eval/misconception (58 AI-written cases); see that folder for the numbers.
"""
import ast
import json
import logging
import os
import re
from dataclasses import dataclass
from fractions import Fraction

from . import guardrails, llm

log = logging.getLogger(__name__)

DEFAULT_PROVIDER = "qwen_finetuned"
MODEL_OFF = ("", "none", "off")       # STEP_FINDER_PROVIDER values that leave only the arithmetic check
MAX_LINES = 12

SYSTEM = (
    "You check a school learner's working against a reference solution. "
    "Find the first step in the learner's working that is wrong. "
    "A different method that is valid and reaches the correct answer is not an error. "
    "If no step is wrong, answer 0. Do not invent errors. "
    'Reply with JSON only: {"first_wrong_step": <number>, "error": "<one short sentence, empty if 0>"}'
)


@dataclass
class Finding:
    step: int       # 1-based line of the working
    line: str       # that line, as the learner wrote it
    error: str      # one sentence from the model; empty for an arithmetic slip
    source: str     # "arithmetic" or "model"


# ---------------------------------------------------------------- reading the learner's message
def split_working(text: str) -> list[str] | None:
    """The message as working steps, or None when it is just an answer or a remark."""
    lines = [line.strip() for line in text.splitlines() if line.strip()][:MAX_LINES]
    if len(lines) >= 2 or (lines and has_arithmetic(lines)):
        return lines
    return None


def has_arithmetic(lines: list[str]) -> bool:
    """True when some line is a calculation such as '50 / 20 = 2.5' (not just 'x = 5')."""
    return any(re.search(r"\d\s*[-+*/x×÷]\s*\(?\s*\d.*=|=.*\d\s*[-+*/x×÷]\s*\(?\s*\d", line) for line in lines)


def final_answer(lines: list[str]) -> str:
    """The answer the working ends on: what follows the last '=' or ':' of the last line."""
    last = re.split(r"[=:]", lines[-1])[-1].strip()
    number = re.fullmatch(r"(?:rs\.?|₹|\$)?\s*(-?\d+(?:\.\d+)?(?:/\d+)?%?)(?:\s+[A-Za-z²°/ ]+)?\.?", last, re.I)
    return number[1] if number else last


# ---------------------------------------------------------------- 1. arithmetic check
def _value(text: str) -> tuple[Fraction, int | None] | None:
    """Exact value of a plain arithmetic expression, plus its decimal places when it is a single decimal."""
    t = re.sub(r"^[A-Za-z' ]+:\s*", "", text.strip())                      # "Answer: 12"
    t = re.sub(r"^(?:rs\.?|₹|\$)\s*", "", t, flags=re.I)                    # "Rs 30"
    t = re.sub(r"\s+[A-Za-z²°]+(?:[ /][A-Za-z²°]+)*\.?$", "", t)            # "30 square cm", "50 km/h"
    t = re.sub(r"(?<=\d)\s*[xX]\s*(?=[\d(])", "*", t).replace("×", "*").replace("÷", "/").replace(",", "")
    if not t or len(t) > 80 or not re.fullmatch(r"[\d\s.+\-*/()]+", t):
        return None
    try:
        value = _eval(ast.parse(t, mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError, RecursionError):
        return None
    places = re.fullmatch(r"-?\d+\.(\d+)", t)
    return value, (len(places[1]) if places else None)


def _eval(node) -> Fraction:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return Fraction(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _eval(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        a, b = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Div):
            return a / b
        return a + b if isinstance(node.op, ast.Add) else a - b if isinstance(node.op, ast.Sub) else a * b
    raise ValueError("not plain arithmetic")


def arithmetic_slip(lines: list[str]) -> int | None:
    """1-based number of the first line whose two sides are not equal, or None."""
    carried = None                      # value the previous line ended on, for lines that start with "="
    for number, line in enumerate(lines, 1):
        parts = [_value(part) for part in line.split("=")]
        if line.lstrip().startswith("="):
            parts[0] = carried
        for left, right in zip(parts, parts[1:]):
            if left is None or right is None:
                continue
            gap, places = abs(left[0] - right[0]), right[1]
            # a rounded decimal on the right is fine (10 / 3 = 3.33); anything else must be exact
            if gap >= Fraction(1, 10 ** places) if places is not None else gap != 0:
                return number
        known = [p for p in parts if p is not None]
        carried = known[-1] if known else None
    return None


# ---------------------------------------------------------------- 2. model check
def build_prompt(question: str, reference: list[str], working: list[str]) -> str:
    ref = "\n".join(f"- {s}" for s in reference)
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(working, 1))
    return f"Question: {question}\n\nReference solution:\n{ref}\n\nLearner's working:\n{steps}"


def parse(reply: str) -> tuple[int | None, str]:
    """(step, error) from the model's reply. step is None when the reply cannot be read."""
    for block in re.findall(r"\{.*?\}", reply, re.S):
        try:
            data = json.loads(block)
            return int(data["first_wrong_step"]), str(data.get("error", ""))
        except (ValueError, KeyError, TypeError):
            continue
    cut_off = re.search(r'"first_wrong_step"\s*:\s*(\d+)', reply)   # reply ended before the JSON closed
    return (int(cut_off[1]), "") if cut_off else (None, "")


def _ask_model(question: str, answer: str, hint: str, working: list[str]) -> tuple[int, str] | None:
    provider = os.environ.get("STEP_FINDER_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider in MODEL_OFF:
        return None
    reference = ([hint] if hint else []) + [f"The correct final answer is {answer}"]
    try:
        reply = llm.get_provider(provider).generate(build_prompt(question, reference, working), SYSTEM, 256)
    except Exception as e:  # not configured, unreachable, quota used up
        log.warning("Step finder model unavailable (%s): %s", provider, type(e).__name__)
        return None
    step, error = parse(reply)
    if step is None or not 1 <= step <= len(working):
        return None                                   # unreadable, "no error" (0) or a step that does not exist
    return step, error.strip()


# ---------------------------------------------------------------- public API
def find(question: str, answer: str, working: list[str], hint: str = "") -> Finding | None:
    """First wrong step of working that led to a wrong answer, or None."""
    slip = arithmetic_slip(working)
    if slip:
        return Finding(slip, working[slip - 1], "", "arithmetic")
    found = _ask_model(question, answer, hint, working)
    if not found:
        return None
    step, error = found
    if guardrails.leaks_answer(error, answer):        # the explanation must not give the answer away
        error = ""
    return Finding(step, working[step - 1], error, "model")
