"""Learner model: how well the learner knows each concept.

Stub: smoothed accuracy per concept (the fallback described in the report).
Swap `readiness` for the trained DKT model behind the same interface; DKT reads
`session_sequence`. History is kept per learner and per course, so courses never mix.
"""
import logging
from collections.abc import Iterable

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ..db import AnswerConceptRow, AnswerRow
from . import akt

_log = logging.getLogger("uvicorn.error")  # shown by default under uvicorn; no app logging config exists


def record(db: Session, learner_id: str, course_id: str, session_id: str, concept_id: str, correct: bool,
           graph_concepts: Iterable[str] = ()) -> None:
    """One answer on `concept_id` (a pack concept or an NCERT chapter), linked to the learning-graph concepts
    it was about, if any."""
    answer = AnswerRow(learner_id=learner_id, course_id=course_id, session_id=session_id,
                       concept_id=concept_id, correct=correct)
    db.add(answer)
    db.flush()
    db.add_all(AnswerConceptRow(answer_id=answer.id, concept_id=c) for c in dict.fromkeys(graph_concepts))
    db.flush()


def stats(db: Session, learner_id: str, course_id: str, concept_id: str) -> tuple[int, int]:
    """(attempts, correct) on a concept: answers recorded on it, or linked to it as a graph concept."""
    linked = select(AnswerConceptRow.answer_id).where(AnswerConceptRow.concept_id == concept_id)
    attempts, correct = db.execute(
        select(func.count(AnswerRow.id), func.coalesce(func.sum(case((AnswerRow.correct, 1), else_=0)), 0))
        .where(AnswerRow.learner_id == learner_id, AnswerRow.course_id == course_id,
               or_(AnswerRow.concept_id == concept_id, AnswerRow.id.in_(linked)))).one()
    return int(attempts), int(correct)


def concept_mastery(db: Session, learner_id: str, course_id: str,
                    concept_ids: Iterable[str]) -> dict[str, tuple[float | None, str | None, int, int]]:
    """For many graph concepts at once: (readiness, "akt" or "accuracy", attempts, correct). Readiness and source
    are None when there is no evidence (no answer on the concept and no AKT estimate). Same rules as
    concept_readiness, with the answers read in two queries instead of a few per concept."""
    right = func.coalesce(func.sum(case((AnswerRow.correct, 1), else_=0)), 0)
    mine = (AnswerRow.learner_id == learner_id, AnswerRow.course_id == course_id)
    counts: dict[str, list[int]] = {}
    for concept, n, ok in [
        *db.execute(select(AnswerConceptRow.concept_id, func.count(AnswerRow.id), right)
                    .join(AnswerRow, AnswerRow.id == AnswerConceptRow.answer_id)
                    .where(*mine).group_by(AnswerConceptRow.concept_id)).all(),
        *db.execute(select(AnswerRow.concept_id, func.count(AnswerRow.id), right)
                    .where(*mine).group_by(AnswerRow.concept_id)).all()]:
        total = counts.setdefault(concept, [0, 0])
        total[0], total[1] = total[0] + int(n), total[1] + int(ok)
    tracer = akt.get_tracer()
    answers = history(db, learner_id, course_id) if tracer else []
    out = {}
    for cid in concept_ids:
        attempts, correct = counts.get(cid, (0, 0))
        p = tracer.predict(cid, answers) if tracer and tracer.skill_of(cid) is not None else None
        if p is not None:
            out[cid] = (p, "akt", attempts, correct)
        elif attempts:
            out[cid] = ((correct + 1) / (attempts + 2), "accuracy", attempts, correct)
        else:
            out[cid] = (None, None, 0, 0)
    return out


def concept_readiness(db: Session, learner_id: str, course_id: str, concept_id: str) -> float | None:
    """Readiness on one learning-graph concept, or None when the learner has no evidence on it yet (no linked
    answer and no AKT estimate), so the caller can fall back to the chapter."""
    p, source = estimate(db, learner_id, course_id, concept_id)
    if source == "akt" or stats(db, learner_id, course_id, concept_id)[0]:
        return p
    return None


def history(db: Session, learner_id: str, course_id: str) -> list[tuple[str, bool]]:
    """All recorded answers of this learner in this course, oldest first."""
    rows = db.execute(select(AnswerRow.concept_id, AnswerRow.correct)
                      .where(AnswerRow.learner_id == learner_id, AnswerRow.course_id == course_id)
                      .order_by(AnswerRow.id)).all()
    return [(c, bool(ok)) for c, ok in rows]


def last_answer_id(db: Session, session_id: str) -> int:
    """The newest answer recorded in this session (0 when none): a mark to count later answers from."""
    return int(db.scalar(select(func.coalesce(func.max(AnswerRow.id), 0)).where(AnswerRow.session_id == session_id)))


def wrong_in_a_row(db: Session, session_id: str, concept_id: str, after_id: int = 0) -> int:
    """Wrong answers at the end of this session's answers on the concept, counting only answers after `after_id`.
    A right answer ends the run."""
    rows = db.scalars(select(AnswerRow.correct)
                      .where(AnswerRow.session_id == session_id, AnswerRow.concept_id == concept_id,
                             AnswerRow.id > after_id)
                      .order_by(AnswerRow.id.desc()).limit(20)).all()
    wrong = 0
    for ok in rows:
        if ok:
            break
        wrong += 1
    return wrong


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
