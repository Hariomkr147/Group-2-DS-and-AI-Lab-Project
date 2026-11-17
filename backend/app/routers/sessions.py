from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionRow, TurnRow, get_db
from ..schemas import MessageIn, SessionCreate, SessionInfo, TutorReply, Turn
from ..security import current_user, limit_messages
from ..services import course_store, ncert, tutor

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get(db: Session, session_id: str, *, for_update: bool = False) -> SessionRow:
    s = db.get(SessionRow, session_id, with_for_update=True if for_update else None)
    if s is None:
        raise HTTPException(404, f"session '{session_id}' not found")
    return s


def _info(db: Session, s: SessionRow) -> SessionInfo:
    turns = db.scalars(select(TurnRow).where(TurnRow.session_id == s.id).order_by(TurnRow.id)).all()
    return SessionInfo(session_id=s.id, learner_id=s.learner_id, course_id=s.course_id,
                       target_concept=s.target_concept, current_concept=s.current_concept,
                       history=[Turn(role=t.role, text=t.text) for t in turns])


@router.post("", response_model=SessionInfo, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db), user: str = Depends(current_user)):
    course_store.get_pack(db, body.course_id)  # 404 if the course does not exist
    pending = None
    if body.course_id == ncert.COURSE_ID:
        if not ncert.configured():
            raise HTTPException(503, "NCERT retrieval is not configured.")
        pending = {"scope": {"grade": body.grade, "subject": body.subject}}
    s = SessionRow(id=uuid4().hex, learner_id=body.learner_id or user, course_id=body.course_id,
                   stack=[], tries=0, pending=pending)
    db.add(s)
    db.commit()
    return _info(db, s)


@router.get("/{session_id}", response_model=SessionInfo)
def get_session(session_id: str, db: Session = Depends(get_db)):
    return _info(db, _get(db, session_id))


@router.post("/{session_id}/messages", response_model=TutorReply)
def send_message(session_id: str, body: MessageIn, db: Session = Depends(get_db), user: str = Depends(current_user)):
    limit_messages(user)
    return tutor.handle_message(db, _get(db, session_id, for_update=True), body.text, body.new_topic)
