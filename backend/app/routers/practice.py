from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from ..db import AssessmentItemRow, SessionRow, get_db
from ..schemas import (AssessmentAnswer, AssessmentRequest, AssessmentResult, DiagnosticRequest,
                       PracticeRequest, Question, QuestionOut)
from ..services import course_store, guardrails, learner_model, ncert, tutor

router = APIRouter(tags=["practice"])


def _out(concept_id: str, q: Question) -> QuestionOut:
    hint = "" if guardrails.leaks_answer(q.hint, q.answer) else q.hint
    return QuestionOut(id=q.id, concept_id=concept_id, text=q.text, hint=hint, difficulty=q.difficulty)


@router.post("/practice", response_model=list[QuestionOut])
def practice(body: PracticeRequest, db: Session = Depends(get_db)):
    """Practice questions for one concept, optionally at a given difficulty. Answers are not returned."""
    return [_out(cid, q) for cid, q in _practice(db, body)]


@router.post("/diagnostics", response_model=list[QuestionOut])
def diagnostic(body: DiagnosticRequest, db: Session = Depends(get_db)):
    """Short test across concepts, lowest level first, to find the learner's starting point."""
    return [_out(cid, q) for cid, q in _diagnostic(db, body)]


def _practice(db: Session, body: PracticeRequest):
    concept = course_store.get_concept(db, body.course_id, body.concept_id)
    questions = [q for q in concept.questions if body.difficulty is None or q.difficulty == body.difficulty]
    return [(concept.id, q) for q in questions[:body.count]]


def _diagnostic(db: Session, body: DiagnosticRequest):
    pack = course_store.get_pack(db, body.course_id)
    return [(c.id, q) for c in sorted(pack.concepts, key=lambda c: c.level)
            for q in c.questions[:body.per_concept]]


@router.post("/assessments", response_model=list[QuestionOut], status_code=201)
def start_assessment(body: AssessmentRequest, db: Session = Depends(get_db)):
    session = db.get(SessionRow, body.session_id)
    if session is None:
        raise HTTPException(404, "Session not found.")
    if session.course_id == ncert.COURSE_ID:
        raise HTTPException(422, "Textbook chat does not have graded assessments.")
    if body.kind == "practice":
        if not body.concept_id:
            raise HTTPException(422, "Choose a concept to practise.")
        questions = _practice(db, PracticeRequest(course_id=session.course_id, concept_id=body.concept_id,
                                                  difficulty=body.difficulty))
    else:
        questions = _diagnostic(db, DiagnosticRequest(course_id=session.course_id))
    out = []
    for concept_id, question in questions:
        item_id = uuid4().hex
        db.add(AssessmentItemRow(id=item_id, session_id=session.id, concept_id=concept_id,
                                 answer_key=question.answer))
        item = _out(concept_id, question)
        out.append(item.model_copy(update={"id": item_id, "hint": item.hint if body.kind == "practice" else ""}))
    db.commit()
    return out


@router.post("/assessments/{item_id}/answer", response_model=AssessmentResult)
def grade_assessment(item_id: str, body: AssessmentAnswer, db: Session = Depends(get_db)):
    item = db.get(AssessmentItemRow, item_id)
    if item is None:
        raise HTTPException(404, "Assessment question not found.")
    correct = tutor.same_answer(body.text, item.answer_key)
    claimed = db.execute(update(AssessmentItemRow).where(
        AssessmentItemRow.id == item_id, AssessmentItemRow.correct.is_(None)
    ).values(correct=correct))
    if claimed.rowcount:
        session = db.get(SessionRow, item.session_id)
        learner_model.record(db, session.learner_id, session.course_id, session.id, item.concept_id, correct)
        db.commit()
        return AssessmentResult(correct=correct)
    db.refresh(item)
    return AssessmentResult(correct=item.correct)
