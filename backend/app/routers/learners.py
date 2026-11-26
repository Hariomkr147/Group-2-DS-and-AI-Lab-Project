from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import SessionRow, get_db
from ..schemas import AnswerIn, ConceptProgress, Progress, SkillLevel
from ..services import course_store, learner_model, ncert

router = APIRouter(prefix="/learners", tags=["learners"])


def _progress(db: Session, learner_id: str, course_id: str) -> Progress:
    rows = []
    for c in course_store.get_pack(db, course_id).concepts:
        attempts, correct = learner_model.stats(db, learner_id, course_id, c.id)
        rows.append(ConceptProgress(
            concept_id=c.id, name=c.name, level=c.level, attempts=attempts, correct=correct,
            readiness=round(learner_model.readiness(db, learner_id, course_id, c.id), 3)))
    return Progress(learner_id=learner_id, course_id=course_id, concepts=rows)


@router.post("/{learner_id}/answers", response_model=Progress, status_code=201)
def record_answer(learner_id: str, body: AnswerIn, db: Session = Depends(get_db)):
    """Record an answer given outside the chat (e.g. the diagnostic test)."""
    course_store.get_concept(db, body.course_id, body.concept_id)
    session = db.get(SessionRow, body.session_id)
    if session is None or session.learner_id != learner_id or session.course_id != body.course_id:
        raise HTTPException(404, "session not found for this learner and course")
    learner_model.record(db, learner_id, body.course_id, body.session_id, body.concept_id, body.correct)
    db.commit()
    return _progress(db, learner_id, body.course_id)


@router.get("/{learner_id}/progress", response_model=Progress)
def get_progress(learner_id: str, course_id: str, db: Session = Depends(get_db)):
    return _progress(db, learner_id, course_id)


@router.get("/{learner_id}/skill", response_model=SkillLevel)
def get_skill(learner_id: str, grade: int = Query(ge=6, le=10), subject: Literal["maths", "science"] = Query(),
              db: Session = Depends(get_db)):
    """NCERT skill level for one class and subject, from the answers the tutor judged in textbook chat."""
    return learner_model.skill_level(db, learner_id, ncert.COURSE_ID, grade, subject)
