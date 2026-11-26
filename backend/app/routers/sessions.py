from datetime import timezone
import json
import logging
import queue
import threading
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import CourseRow, SessionLocal, SessionRow, TurnDetailRow, TurnRow, TurnStepRow, get_db
from ..schemas import MessageIn, SessionCreate, SessionInfo, TutorReply, Turn
from ..security import current_user, limit_messages
from ..services import course_store, ncert, trace, tutor

router = APIRouter(prefix="/sessions", tags=["sessions"])
log = logging.getLogger(__name__)


def _get(db: Session, session_id: str, *, for_update: bool = False) -> SessionRow:
    s = db.get(SessionRow, session_id, with_for_update=True if for_update else None)
    if s is None:
        raise HTTPException(404, f"session '{session_id}' not found")
    return s


def _info(db: Session, s: SessionRow) -> SessionInfo:
    turns = db.execute(select(TurnRow, TurnDetailRow.reply, TurnDetailRow.request_id, TurnStepRow.steps)
                       .outerjoin(TurnDetailRow, TurnDetailRow.turn_id == TurnRow.id)
                       .outerjoin(TurnStepRow, TurnStepRow.turn_id == TurnRow.id)
                       .where(TurnRow.session_id == s.id).order_by(TurnRow.id))
    return SessionInfo(session_id=s.id, learner_id=s.learner_id, course_id=s.course_id,
                       target_concept=s.target_concept, current_concept=s.current_concept,
                       history=[Turn(role=t.role, text=t.text, detail=detail, request_id=request_id, steps=steps)
                                for t, detail, request_id, steps in turns])


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


@router.get("")
def previous_chats(before: int | None = Query(None, gt=0), db: Session = Depends(get_db),
                   user: str = Depends(current_user)):
    turns = (select(TurnRow.session_id, func.min(TurnRow.id).label("first"), func.max(TurnRow.id).label("last"),
                    func.max(TurnRow.created_at).label("updated"))
             .join(SessionRow, SessionRow.id == TurnRow.session_id)
             .where(SessionRow.learner_id == user, TurnRow.role == "learner")
             .group_by(TurnRow.session_id).subquery())
    query = (select(SessionRow, CourseRow.title, TurnRow.text, turns.c.last, turns.c.updated)
             .select_from(SessionRow)
             .join(turns, turns.c.session_id == SessionRow.id)
             .join(TurnRow, TurnRow.id == turns.c.first)
             .join(CourseRow, CourseRow.id == SessionRow.course_id))
    if before is not None:
        query = query.where(turns.c.last < before)
    rows = db.execute(query.order_by(turns.c.last.desc()).limit(21)).all()
    return {"items": [{"session_id": s.id, "course_id": s.course_id, "course_title": title,
                       "title": first[:160], "updated_at": updated.replace(tzinfo=timezone.utc),
                       "scope": (s.pending or {}).get("scope", {})}
                      for s, title, first, last, updated in rows[:20]],
            "next": rows[19].last if len(rows) > 20 else None}


@router.get("/{session_id}", response_model=SessionInfo)
def get_session(session_id: str, db: Session = Depends(get_db)):
    return _info(db, _get(db, session_id))


def _turn(db: Session, session_id: str, body: MessageIn, user: str,
          on_step=None) -> tuple[TutorReply | dict, list | None]:
    """Run one turn and save it with the steps each layer reported (passed on to `on_step` as they happen).
    Returns the reply and the answers to judge once it is sent (None for a replay)."""
    steps: list[dict] = []

    def record(step: dict) -> None:
        steps.append(step)
        if on_step:
            on_step(step)

    with trace.collect(record):
        trace.emit("received", "Message received")
        return _run_turn(db, session_id, body, user, steps)


def _run_turn(db: Session, session_id: str, body: MessageIn, user: str,
              steps: list[dict]) -> tuple[TutorReply | dict, list | None]:
    session = _get(db, session_id, for_update=True)
    request_id = str(body.request_id or uuid4())
    message = body.model_dump(exclude={"request_id"})
    if body.topic_heading is None:
        message.pop("topic_heading")  # keep request IDs replayable for turns saved before the field existed
    existing = db.get(TurnDetailRow, (session_id, request_id))
    if existing:
        trace.emit("replay", "Already answered", "this message was sent before, so the saved reply is returned")
        return _replay(existing, message), None
    limit_messages(user)
    reply = tutor.handle_message(db, session, body.text, body.new_topic, body.concept_id, topic_heading=body.topic_heading)
    try:
        db.flush()
        turn_id = db.scalars(select(TurnRow.id).where(TurnRow.session_id == session_id)
                             .order_by(TurnRow.id.desc()).limit(1)).one()
        db.add(TurnDetailRow(session_id=session_id, request_id=request_id, turn_id=turn_id,
                             message=message, reply=reply.model_dump(mode="json")))
        db.add(TurnStepRow(turn_id=turn_id, steps=list(steps)))   # replays emit no steps and save none
        db.commit()
    except IntegrityError:
        db.info.pop(tutor.PENDING_JUDGEMENTS, None)          # the turn was a duplicate: nothing new to judge
        db.rollback()
        existing = db.get(TurnDetailRow, (session_id, request_id))
        if existing is None:
            raise
        return _replay(existing, message), None
    return reply, db.info.pop(tutor.PENDING_JUDGEMENTS, None)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_turn(session_id: str, body: MessageIn, user: str):
    """Server-sent events for one turn: `step` events as each layer works, then `reply` (the TutorReply)
    or `error` ({"status", "detail"}). The turn runs in its own thread with its own database session, so it
    finishes and is saved even if the browser disconnects; resending the same request_id replays it."""
    events: queue.Queue = queue.Queue()

    def work():
        judgements = None
        try:
            with SessionLocal() as db:
                reply, judgements = _turn(db, session_id, body, user, on_step=lambda step: events.put(("step", step)))
            events.put(("reply", reply if isinstance(reply, dict) else reply.model_dump(mode="json")))
        except HTTPException as error:
            events.put(("error", {"status": error.status_code, "detail": error.detail}))
        except Exception as error:
            log.exception("Streamed turn failed (%s)", type(error).__name__)
            events.put(("error", {"status": 500, "detail": "The tutor could not finish this turn."}))
        finally:
            events.put(None)
        if judgements:                                        # after the reply has gone out, as on the JSON path
            tutor.judge_and_record(judgements)

    threading.Thread(target=work, name=f"turn-{session_id[:8]}", daemon=True).start()
    while (item := events.get()) is not None:
        yield _sse(*item)


@router.post("/{session_id}/messages", response_model=TutorReply)
def send_message(session_id: str, body: MessageIn, background: BackgroundTasks, request: Request,
                 db: Session = Depends(get_db), user: str = Depends(current_user)):
    """One tutoring turn. With `Accept: text/event-stream` the reply is streamed as server-sent events
    (see _stream_turn) so the client can show each layer at work; otherwise it is one JSON TutorReply."""
    if "text/event-stream" in request.headers.get("accept", ""):
        _get(db, session_id)                                  # a missing session is a real 404, before the stream
        return StreamingResponse(_stream_turn(session_id, body, user), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
    reply, judgements = _turn(db, session_id, body, user)
    if judgements:                                            # runs after the reply is sent: no added latency
        background.add_task(tutor.judge_and_record, judgements)
    return reply


def _replay(existing: TurnDetailRow, message: dict) -> dict:
    if existing.message != message:
        raise HTTPException(409, "This request ID was already used for a different message.")
    return existing.reply
