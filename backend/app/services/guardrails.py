"""Input and output checks that keep the tutor on topic and stop answer leakage.

Stub: keyword rules. Replace `classify_input` with a small trained classifier and
`leaks_answer` with a stronger check (the report lists other methods to explore).
"""
import re

from sqlalchemy.orm import Session

from ..schemas import InputLabel
from . import retrieval

_ANSWER_REQUEST = re.compile(r"\b(just )?(give|tell|show) (me )?the (final )?answer\b|\bsolve (it|this) for me\b", re.I)


def classify_input(db: Session, text: str, course_id: str) -> InputLabel:
    if _ANSWER_REQUEST.search(text):
        return InputLabel.ANSWER_REQUEST
    if re.fullmatch(r"[\s\d.,/%+\-*x÷=]+", text):  # a bare number is an answer to a question
        return InputLabel.ON_TOPIC
    return InputLabel.ON_TOPIC if retrieval.best_concept(db, course_id, text) else InputLabel.OFF_TOPIC


def leaks_answer(reply: str, answer: str | None) -> bool:
    if not answer:
        return False
    return re.search(rf"(?<![\w.]){re.escape(answer.strip())}(?![\w.])", reply) is not None
