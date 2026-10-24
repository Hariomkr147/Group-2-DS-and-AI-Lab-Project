"""One tutoring turn: guardrails -> learner model -> controller -> Socratic model -> guardrails."""
from sqlalchemy.orm import Session

from ..db import SessionRow, TurnRow
from ..schemas import Action, Concept, InputLabel, Question, Resource, TutorReply
from . import controller, course_store, guardrails, learner_model, misconception, retrieval, socratic


def _norm(text: str) -> str:
    return text.strip().lower().replace(" ", "").rstrip(".")


def _next_question(concept: Concept) -> Question | None:
    return concept.questions[0] if concept.questions else None


def _resource(concept: Concept) -> Resource | None:
    if not concept.materials:
        return None
    m = concept.materials[0]
    return Resource(source=m.source, page=m.page, url=m.url)


def _finish(db: Session, session: SessionRow, learner_text: str, reply: TutorReply) -> TutorReply:
    db.add_all([TurnRow(session_id=session.id, role="learner", text=learner_text),
                TurnRow(session_id=session.id, role="tutor", text=reply.reply)])
    db.commit()
    return reply


def handle_message(db: Session, session: SessionRow, text: str) -> TutorReply:
    label = guardrails.classify_input(db, text, session.course_id)

    # Answer requests, and off-topic messages (longer than a short answer), never reach the learner model.
    if label == InputLabel.ANSWER_REQUEST or (label == InputLabel.OFF_TOPIC and (
            session.pending is None or len(text.split()) > 4)):
        msg = socratic.REDIRECT_ANSWER if label == InputLabel.ANSWER_REQUEST else socratic.REDIRECT_OFF_TOPIC
        return _finish(db, session, text, TutorReply(reply=msg, action=Action.REDIRECT, label=label))

    if session.pending is None:
        concept_id = retrieval.best_concept(db, session.course_id, text)
        if concept_id is None:
            return _finish(db, session, text, TutorReply(
                reply=socratic.REDIRECT_OFF_TOPIC, action=Action.REDIRECT, label=InputLabel.OFF_TOPIC))
        session.target_concept = session.current_concept = concept_id
        session.stack, session.tries = [], 0
        action = Action.ASK
    else:
        asked = Question(**session.pending)
        correct = _norm(text) == _norm(asked.answer)
        misconception.detect(asked.text, text, asked.answer)
        learner_model.record(db, session.learner_id, session.course_id, session.id,
                             session.current_concept, correct)
        decision = controller.decide(db, session, correct)
        action = decision.action
        session.current_concept = decision.concept_id

    concept = course_store.get_concept(db, session.course_id, session.current_concept)
    if action in (Action.HINT, Action.PROBE):
        question = Question(**session.pending)  # ask the same question again
    elif action == Action.DONE:
        question = None
    else:
        question = _next_question(concept)
    session.pending = question.model_dump() if question else None

    reply_text = socratic.write(action, concept, question)
    if guardrails.leaks_answer(reply_text, question.answer if question else None):
        reply_text = f"Let's think step by step. What do you already know about {concept.name}?"

    return _finish(db, session, text, TutorReply(
        reply=reply_text, action=action, label=InputLabel.ON_TOPIC,
        concept_id=concept.id, level=concept.level, resource=_resource(concept)))
