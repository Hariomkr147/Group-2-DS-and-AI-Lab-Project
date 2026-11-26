from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import SessionRow, get_db
from ..schemas import AnswerIn, ConceptProgress, LearnerGraph, LearnerState, Progress, SavedTopic, SkillLevel
from ..security import current_user
from ..services import course_store, learner_graph, learner_model, ncert, tutor

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


@router.get("/{learner_id}/graph", response_model=LearnerGraph)
def get_learner_graph(learner_id: str,
                      grade: int | None = Query(None, ge=6, le=10),
                      subject: Literal["maths", "science"] | None = Query(None),
                      book_code: str | None = Query(None, min_length=1, max_length=80),
                      chapter: int | None = Query(None, ge=1),
                      db: Session = Depends(get_db), user: str = Depends(current_user)):
    """The NCERT learning graph with this learner's mastery on each concept (mastered, learning, struggling, ready,
    unseen), the concepts ready to learn next and the ones to review. Filters as GET /courses/ncert/graph.
    Only the signed-in learner can read their own."""
    if learner_id != user:
        raise HTTPException(403, "You can only read your own learning graph.")
    return learner_graph.learner_graph(db, learner_id, {"grade": grade, "subject": subject,
                                                        "book_code": book_code, "chapter": chapter})


@router.get("/{learner_id}/state", response_model=LearnerState)
def get_state(learner_id: str, course_id: str = ncert.COURSE_ID, db: Session = Depends(get_db),
              user: str = Depends(current_user)):
    """The learner's place in the course across sessions: the last open topic and the detour to climb back through.
    Only the signed-in learner can read their own."""
    if learner_id != user:
        raise HTTPException(403, "You can only read your own learner state.")
    saved = tutor.saved_state(db, learner_id, course_id)
    if saved is None or not saved.topic:
        return LearnerState(learner_id=learner_id, course_id=course_id)
    return LearnerState(
        learner_id=learner_id, course_id=course_id, session_id=saved.session_id, updated_at=saved.updated_at,
        topic=SavedTopic(heading=saved.topic["heading"], chapter=saved.topic["chapter"]),
        detour=[SavedTopic(heading=e["heading"], chapter=e["chapter"]) for e in saved.stack or []])
