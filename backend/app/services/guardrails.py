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
from . import misconception, router_model

log = logging.getLogger(__name__)

_ANSWER_REQUEST = re.compile(r"\b(just )?(give|tell|show) (me )?the (final )?answer\b|\bsolve (it|this) for me\b", re.I)
_ANSWER_KEY = re.compile(
    r"\b(?:show|reveal|print|dump|give|disclose|expose|provide|share)\b.{0,60}"
    r"\b(?:answer (?:key|bank|sheet)|marking (?:scheme|key)|(?:hidden|private|teacher.only) (?:answers?|solutions?))\b",
    re.I | re.S,
)
_BYPASS = re.compile(
    r"^(?:please\s+)?(?:ignore|disregard|override|bypass)\s+(?:(?:the|your|all|previous|prior|earlier)\s+)*"
    r"(?:instructions|system prompt|guardrails)\b",
    re.I,
)
_NEGATED_ANSWER = re.compile(r"\b(?:don't|do not|never)\s+(?:give|tell|show|solve)\s+(?:me\s+)?"
                             r"the\s+(?:final\s+)?answer\b", re.I)
_HELP = re.compile(
    r"\b(?:hints?|clues?|i (?:don't|do not|didn't|cannot|can't) (?:understand|follow|see)"
    r"|i(?:'m| am) (?:confused|lost|stuck)|explain (?:that|it|this|why|how)|what (?:next|should i do next))\b"
    r"|^why\b",
    re.I,
)
_TOPIC_SWITCH = re.compile(
    r"\b(?:switch (?:to|topics?)|change (?:the )?topic|move (?:on |over )?to"
    r"|(?:let's|let’s|can we|could we|i want to|i'd like to) (?:learn|study|practice))\b"
    r"|^teach me\b",
    re.I,
)
_NUMBER = re.compile(r"[\d\s.+\-/,]+%?")
_ABUSE = re.compile(
    r"\b(?:idiots?|stupid|dumb|useless|moron(?:ic|s)?|imbecile|retard(?:ed)?|trash|garbage|pathetic|"
    r"shut\s*up|screw you|fuck\w*|shit\w*|bitch\w*|bastard|asshole|crap|damn you|go to hell)\b", re.I)


def is_abusive(text: str) -> bool:
    return bool(_ABUSE.search(text.replace("’", "'")))


def numeric_answer(text: str) -> bool:
    return bool(len(text) <= 80 and _NUMBER.fullmatch(text) and misconception.to_value(text) is not None)


def requests_answer(text: str) -> bool:
    text = text.replace("’", "'")
    return bool(_BYPASS.search(text) or _ANSWER_KEY.search(text) or _ANSWER_REQUEST.search(_NEGATED_ANSWER.sub("", text)))


def asks_for_help(text: str) -> bool:
    return bool(_HELP.search(text.replace("’", "'")))


def requests_topic_switch(text: str) -> bool:
    return bool(_TOPIC_SWITCH.search(text))


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
        return intent, scope_label
    except Exception as error:
        log.warning("Message router prediction failed (%s)", type(error).__name__)
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
    return bool(results) and any(value in results for value in _values(reply))


def leaks_answer(reply: str, answer: str | None) -> bool:
    if not answer:
        return False
    # the answer may end a sentence ("... is 10."), but must not be part of a longer number ("10.5", "110")
    return re.search(rf"(?<![\w.]){re.escape(answer.strip())}(?!\w|\.\d)", reply) is not None
