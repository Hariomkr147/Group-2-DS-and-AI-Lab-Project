from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import DiagnosticRequest, PracticeRequest, Question, QuestionOut
from ..services import course_store

router = APIRouter(tags=["practice"])


def _out(concept_id: str, q: Question) -> QuestionOut:
    return QuestionOut(id=q.id, concept_id=concept_id, text=q.text, hint=q.hint, difficulty=q.difficulty)


@router.post("/practice", response_model=list[QuestionOut])
def practice(body: PracticeRequest, db: Session = Depends(get_db)):
    """Practice questions for one concept, optionally at a given difficulty. Answers are not returned."""
    concept = course_store.get_concept(db, body.course_id, body.concept_id)
    qs = [q for q in concept.questions if body.difficulty is None or q.difficulty == body.difficulty]
    return [_out(concept.id, q) for q in qs[:body.count]]


@router.post("/diagnostics", response_model=list[QuestionOut])
def diagnostic(body: DiagnosticRequest, db: Session = Depends(get_db)):
    """Short test across concepts, lowest level first, to find the learner's starting point."""
    pack = course_store.get_pack(db, body.course_id)
    out = []
    for c in sorted(pack.concepts, key=lambda c: c.level):
        out += [_out(c.id, q) for q in c.questions[:body.per_concept]]
    return out
