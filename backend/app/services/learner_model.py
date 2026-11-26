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
    """Chance the learner answers this concept correctly next (0 to 1)."""
    return estimate(db, learner_id, course_id, concept_id)[0]


def estimate(db: Session, learner_id: str, course_id: str, concept_id: str,
             answers: list[tuple[str, bool]] | None = None) -> tuple[float, str]:
    """(chance of a correct next answer, "akt" or "accuracy").

    Uses the trained AKT when KT_MODEL=akt and the concept has a mapped skill and the learner has
    mapped history; otherwise smoothed accuracy. `answers` is the course history, when the caller has it."""
    tracer = akt.get_tracer()
    if tracer is None:
        why = "KT_MODEL is not akt or AKT failed to load"
    elif tracer.skill_of(concept_id) is None:
        why = "concept not in concept_skill_map.json"
    else:
        p = tracer.predict(concept_id, history(db, learner_id, course_id) if answers is None else answers)
        if p is not None:
            _log.info("readiness concept=%s source=akt p=%.3f", concept_id, p)
            return p, "akt"
        why = "no mapped answer history yet"
    if answers is None:
        attempts, correct = stats(db, learner_id, course_id, concept_id)
    else:
        mine = [ok for c, ok in answers if c == concept_id]
        attempts, correct = len(mine), sum(mine)
    p = (correct + 1) / (attempts + 2)  # unseen concept = 0.5
    _log.info("readiness concept=%s source=smoothed p=%.3f (%s)", concept_id, p, why)
    return p, "accuracy"


def skill_level(db: Session, learner_id: str, course_id: str, grade: int, subject: str) -> dict:
    """Skill in one NCERT class and subject on a 1 to 10 scale: the readiness of each chapter the learner has
    answered in, weighted by its answers. level is None until there is a graded answer."""
    answers = history(db, learner_id, course_id)
    prefix = f"{grade}-{subject}-"
    counts: dict[str, int] = {}
    for c, _ in answers:
        if c.startswith(prefix):
            counts[c] = counts.get(c, 0) + 1
    total = sum(counts.values())
    correct = sum(ok for c, ok in answers if c.startswith(prefix))
    if not total:
        return {"grade": grade, "subject": subject, "level": None, "source": None, "answers": 0, "correct": 0}
    scored = {c: estimate(db, learner_id, course_id, c, answers) for c in counts}
    p = sum(scored[c][0] * n for c, n in counts.items()) / total
    sources = {source for _, source in scored.values()}
    return {"grade": grade, "subject": subject, "level": max(1, min(10, round(1 + 9 * p))),
            "source": sources.pop() if len(sources) == 1 else "mixed", "answers": total, "correct": correct}


def session_sequence(db: Session, learner_id: str, course_id: str, session_id: str) -> list[tuple[str, bool]]:
    rows = db.execute(select(AnswerRow.concept_id, AnswerRow.correct)
                      .where(AnswerRow.learner_id == learner_id, AnswerRow.course_id == course_id,
                             AnswerRow.session_id == session_id).order_by(AnswerRow.id)).all()
    return [(c, bool(ok)) for c, ok in rows]
