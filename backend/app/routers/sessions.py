from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionRow, TurnDetailRow, TurnRow, get_db
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
    turns = db.execute(select(TurnRow, TurnDetailRow.reply, TurnDetailRow.request_id)
                       .outerjoin(TurnDetailRow, TurnDetailRow.turn_id == TurnRow.id)
                       .where(TurnRow.session_id == s.id).order_by(TurnRow.id))
    return SessionInfo(session_id=s.id, learner_id=s.learner_id, course_id=s.course_id,
                       target_concept=s.target_concept, current_concept=s.current_concept,
                       history=[Turn(role=t.role, text=t.text, detail=detail, request_id=request_id)
                                for t, detail, request_id in turns])


@router.post("", response_model=SessionInfo, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db), user: str = Depends(current_user)):
    course_store.get_pack(db, body.course_id)  # 404 if the course does not exist
    pending = None
    if body.course_id == ncert.COURSE_ID:
        if not ncert.configured():
            raise HTTPException(503, "NCERT retrieval is not configured.")
        pending = {"scope": (body.chapter.model_dump() if body.chapter
                             else {"grade": body.grade, "subject": body.subject})}
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
    session = _get(db, session_id, for_update=True)
    request_id = str(body.request_id or uuid4())
    message = body.model_dump(exclude={"request_id"})
    existing = db.get(TurnDetailRow, (session_id, request_id))
    if existing:
        return _replay(existing, message)
    limit_messages(user)
    reply = tutor.handle_message(db, session, body.text, body.new_topic, body.concept_id)
    try:
        db.flush()
        turn_id = db.scalars(select(TurnRow.id).where(TurnRow.session_id == session_id)
                             .order_by(TurnRow.id.desc()).limit(1)).one()
        db.add(TurnDetailRow(session_id=session_id, request_id=request_id, turn_id=turn_id,
                             message=message, reply=reply.model_dump(mode="json")))
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.get(TurnDetailRow, (session_id, request_id))
        if existing is None:
            raise
        return _replay(existing, message)
    return reply


def _replay(existing: TurnDetailRow, message: dict) -> dict:
    if existing.message != message:
        raise HTTPException(409, "This request ID was already used for a different message.")
    return existing.reply
