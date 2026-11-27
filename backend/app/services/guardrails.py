"""Local intent and scope classification and deterministic answer checks."""
from fractions import Fraction
from functools import lru_cache
import logging
from pathlib import Path
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import ConceptRow, CourseRow, SessionRow, TurnRow
from ..schemas import Question
from . import misconception, router_model, trace

log = logging.getLogger(__name__)

_NUMBER = re.compile(r"[\d\s.+\-/,]+%?")


def numeric_answer(text: str) -> bool:
    return bool(len(text) <= 80 and _NUMBER.fullmatch(text) and misconception.to_value(text) is not None)


ANSWER_REQUEST_INTENTS = ("answer_request", "bypass_attempt")
# Below the normal cutoff the router's top label is often still right for answer requests ("Just give me the
# answer" at 0.45). From this confidence up it is returned as UNSURE_ANSWER_REQUEST for Qwen to confirm.
# 0.3 was picked on the dev split: 6/9 answer requests caught, no false redirects (3/9 at the 0.5 cutoff).
UNSURE_ANSWER_REQUEST_CUTOFF = 0.3
UNSURE_ANSWER_REQUEST = "unsure_answer_request"


@lru_cache(maxsize=1)
def _load_router():
    try:
        import joblib
        import sklearn

        bundle = joblib.load(Path(__file__).with_name("message_router.joblib"))
        if (bundle["version"] != router_model.ARTIFACT_VERSION
                or bundle["sklearn_version"] != sklearn.__version__
                or set(bundle["heads"]) != {"intent", "scope"}
                or set(bundle["thresholds"]) != {"intent", "scope"}):
            raise ValueError("Unexpected message router artifact")
        return bundle
    except Exception as error:
        log.warning("Message router unavailable (%s)", type(error).__name__)
        return None


def classify_input(db: Session, session: SessionRow, text: str, question: Question | None) -> tuple[str, str]:
    bundle = _load_router()
    if bundle is None:
        trace.emit("router", "Intent classifier (TF-IDF)", "unavailable, so both labels are uncertain")
        return "uncertain", "uncertain"
    course = db.get(CourseRow, session.course_id)
    state = session.pending or {}
    scope = state.get("scope", {})
    subject = course.subject.lower()
    subjects = tuple(name for name, matches in (
        ("maths", ("maths", "mathematics", "math")), ("science", ("science",)),
    ) if any(re.search(rf"\b{value}\b", subject) for value in matches)) or (subject,)
    if scope.get("subject"):
        subjects = (scope["subject"],)
    concept = None
    if state.get("chapter"):
        concept = state.get("chapter_heading") or session.current_concept
    elif session.current_concept:
        row = db.get(ConceptRow, (session.course_id, session.current_concept))
        concept = row.name if row else session.current_concept
    turns = db.execute(select(TurnRow.role, TurnRow.text).where(TurnRow.session_id == session.id)
                       .order_by(TurnRow.id.desc()).limit(6)).all()
    answer_type = None
    if question:
        answer_type = "number" if numeric_answer(question.answer) else "short_text"
    premise = router_model.format_context(
        text, course=course.title, subjects=subjects, concept=concept,
        question=question.text if question else None, answer_type=answer_type,
        recent=[("student" if role == "learner" else role, message) for role, message in reversed(turns)],
        grade=scope.get("grade"),
    )
    try:
        result = router_model.predict(bundle["encoder"], bundle["heads"], premise)
        intent, scope_label = (
            result[name][0] if result[name][1] >= bundle["thresholds"][name] else "uncertain"
            for name in ("intent", "scope")
        )
        label, confidence = result["intent"]
        if intent == "uncertain" and label in ANSWER_REQUEST_INTENTS and confidence >= UNSURE_ANSWER_REQUEST_CUTOFF:
            intent = UNSURE_ANSWER_REQUEST
        trace.emit("router", "Intent classifier (TF-IDF)",
                   f"intent: {label.replace('_', ' ')} ({confidence:.0%}), "
                   f"scope: {result['scope'][0]} ({result['scope'][1]:.0%})"
                   + ("; low confidence, so treated as unsure" if intent in ("uncertain", UNSURE_ANSWER_REQUEST) else ""))
        return intent, scope_label
    except Exception as error:
        log.warning("Message router prediction failed (%s)", type(error).__name__)
        trace.emit("router", "Intent classifier (TF-IDF)", "failed, so both labels are uncertain")
        return "uncertain", "uncertain"


_VALUE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:/\d+)?(?!\w|\.\d)")
MAX_PROBLEM_NUMBERS = 6       # more numbers than this is working or a table, not a short problem


def _values(text: str) -> list[Fraction]:
    values = []
    for match in _VALUE.findall(text):
        try:
            value = Fraction(match)
        except (ValueError, ZeroDivisionError):
            continue
        if value not in values:
            values.append(value)
    return values


def likely_results(problem: str) -> set[Fraction]:
    """Values a reply should not state for a problem nobody stored an answer for: the sum and product of all its
    numbers and every pairwise sum, difference, product and quotient. Numbers the student wrote and the trivial
    0 and 1 are left out, so restating the question or saying "step 1" is not a leak."""
    numbers = _values(problem)
    if not 2 <= len(numbers) <= MAX_PROBLEM_NUMBERS:
        return set()
    total, product = sum(numbers, Fraction(0)), Fraction(1)
    for number in numbers:
        product *= number
    results = {total, product}
    for i, a in enumerate(numbers):
        for b in numbers[i + 1:]:
            results |= {a + b, a * b, abs(a - b)}
            results |= {x / y for x, y in ((a, b), (b, a)) if y}
    return results - set(numbers) - {Fraction(0), Fraction(1)}


def leaks_result(reply: str, problem: str) -> bool:
    """True when the reply states a likely result of the student's problem (see likely_results). Works without a
    known answer, so it also guards free-form NCERT questions."""
    results = likely_results(problem)
    leaked = bool(results) and any(value in results for value in _values(reply))
    if leaked:
        trace.emit("output_check", "Output guardrail", "a draft stated a likely result of the problem, so it was replaced")
    return leaked


def leaks_answer(reply: str, answer: str | None) -> bool:
    if not answer:
        return False
    # the answer may end a sentence ("... is 10."), but must not be part of a longer number ("10.5", "110")
    leaked = re.search(rf"(?<![\w.]){re.escape(answer.strip())}(?!\w|\.\d)", reply) is not None
    if leaked:
        trace.emit("output_check", "Output guardrail", "a draft contained the answer, so it was replaced")
    return leaked
