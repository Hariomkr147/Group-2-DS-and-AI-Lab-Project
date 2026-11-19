"""Learner model: how well the learner knows each concept.

Stub: smoothed accuracy per concept (the fallback described in the report).
Swap `readiness` for the trained DKT model behind the same interface; DKT reads
`session_sequence`. History is kept per learner and per course, so courses never mix.
"""
import logging

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db import AnswerRow
from . import akt

_log = logging.getLogger("uvicorn.error")  # shown by default under uvicorn; no app logging config exists


def record(db: Session, learner_id: str, course_id: str, session_id: str, concept_id: str, correct: bool) -> None:
    db.add(AnswerRow(learner_id=learner_id, course_id=course_id, session_id=session_id,
                     concept_id=concept_id, correct=correct))
    db.flush()


def stats(db: Session, learner_id: str, course_id: str, concept_id: str) -> tuple[int, int]:
    attempts, correct = db.execute(
        select(func.count(AnswerRow.id), func.coalesce(func.sum(case((AnswerRow.correct, 1), else_=0)), 0))
        .where(AnswerRow.learner_id == learner_id, AnswerRow.course_id == course_id,
               AnswerRow.concept_id == concept_id)).one()
    return int(attempts), int(correct)


def history(db: Session, learner_id: str, course_id: str) -> list[tuple[str, bool]]:
    """All recorded answers of this learner in this course, oldest first."""
    rows = db.execute(select(AnswerRow.concept_id, AnswerRow.correct)
                      .where(AnswerRow.learner_id == learner_id, AnswerRow.course_id == course_id)
                      .order_by(AnswerRow.id)).all()
    return [(c, bool(ok)) for c, ok in rows]


def readiness(db: Session, learner_id: str, course_id: str, concept_id: str) -> float:
    """Chance the learner answers this concept correctly next (0 to 1).

    Uses the trained AKT when KT_MODEL=akt and the concept has a mapped skill and the learner has
    mapped history; otherwise smoothed accuracy."""
    tracer = akt.get_tracer()
    if tracer is None:
        why = "KT_MODEL is not akt or AKT failed to load"
    elif concept_id not in tracer.mapping:
        why = "concept not in concept_skill_map.json"
    else:
        p = tracer.predict(concept_id, history(db, learner_id, course_id))
        if p is not None:
            _log.info("readiness concept=%s source=akt p=%.3f", concept_id, p)
            return p
        why = "no mapped answer history yet"
    attempts, correct = stats(db, learner_id, course_id, concept_id)
    p = (correct + 1) / (attempts + 2)  # unseen concept = 0.5
    _log.info("readiness concept=%s source=smoothed p=%.3f (%s)", concept_id, p, why)
    return p


def session_sequence(db: Session, learner_id: str, course_id: str, session_id: str) -> list[tuple[str, bool]]:
    rows = db.execute(select(AnswerRow.concept_id, AnswerRow.correct)
                      .where(AnswerRow.learner_id == learner_id, AnswerRow.course_id == course_id,
                             AnswerRow.session_id == session_id).order_by(AnswerRow.id)).all()
    return [(c, bool(ok)) for c, ok in rows]
