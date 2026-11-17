"""One tutoring turn: guardrails -> learner model -> controller -> Socratic model -> guardrails."""
import re

from sqlalchemy.orm import Session

from ..db import SessionRow, TurnRow
from ..schemas import Action, Concept, InputLabel, Question, Resource, TutorReply
from . import controller, course_store, guardrails, learner_model, misconception, ncert, retrieval, socratic, step_finder

ASK_FOR_WORKING = "Show your steps, one per line, so I can see where it went wrong."


def _norm(text: str) -> str:
    return text.strip().lower().replace(" ", "").rstrip(".")


def _same(attempt: str, answer: str) -> bool:
    """Same text, or the same number written differently (0.5 and 1/2)."""
    if _norm(attempt) == _norm(answer):
        return True
    a, b = misconception.to_value(attempt), misconception.to_value(answer)
    return a is not None and a == b


def _next_question(concept: Concept, seen: list[str]) -> Question | None:
    """Easiest question not yet asked this session; once all are used, the one asked longest ago."""
    if not concept.questions:
        return None
    unseen = [q for q in concept.questions if q.id not in seen]
    if unseen:
        return min(unseen, key=lambda q: q.difficulty)  # min keeps file order on ties
    by_id = {q.id: q for q in concept.questions}
    return next(by_id[i] for i in seen if i in by_id)


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


def _handle_ncert(db: Session, session: SessionRow, text: str, new_topic: bool) -> TutorReply:
    if guardrails.requests_answer(text):
        return _finish(db, session, text, TutorReply(
            reply=socratic.REDIRECT_ANSWER, action=Action.REDIRECT, label=InputLabel.ANSWER_REQUEST))

    state = session.pending or {}
    scope = state.get("scope", {})
    chapter = None if new_topic else state.get("chapter")
    previous = state.get("question", "")
    # shortcut: pattern-based follow-ups, upgrade after evaluating real conversations.
    followup = chapter and (
        re.fullmatch(r"[\s\d.,/%+\-*x÷=]+", text)
        or re.match(r"(?i)^(i (?:got|tried|think|used)|what next|why (?:is|does) (?:that|it)|(?:give me )?a hint|hint|can you explain (?:that|it))\b", text)
    )
    clarification = re.fullmatch(
        r"(?i)(?:(?:class|grade)\s+([6-9]|10)(?:\s+(maths|science))?|(maths|science))[.!]?", text)
    query = text
    if clarification and state.get("clarify") and not new_topic:
        grade, subject, subject_only = clarification.groups()
        scope = {**scope, "grade": int(grade) if grade else scope.get("grade"),
                 "subject": (subject or subject_only or scope.get("subject") or "").lower() or None}
        query = previous

    if followup:
        passages = ncert.rank(f"{previous}\n{query}", chapter, limit=1)
    else:
        passages = ncert.rank(query, scope, limit=2, chapters=True)

    if not passages or passages[0]["score"] < ncert.MIN_SCORE:
        if not followup:
            session.pending = {"scope": scope, "question": query, "clarify": True}
        message = ("Which part of the current textbook topic are you working on?" if chapter else
                   "I couldn't find a matching NCERT passage. What class, subject or textbook topic is this about?")
        return _finish(db, session, text, TutorReply(
            reply=message, action=Action.REDIRECT, label=InputLabel.OFF_TOPIC))

    best = passages[0]
    if len(passages) > 1 and best["score"] - passages[1]["score"] < ncert.CHAPTER_MARGIN:
        other = passages[1]
        if best["grade"] != other["grade"] or best["subject"] != other["subject"]:
            session.pending = {"scope": scope, "question": query, "clarify": True}
            return _finish(db, session, text, TutorReply(
                reply=f"This could be Class {best['grade']} {best['subject']} or Class {other['grade']} "
                      f"{other['subject']}. Which class and subject are you studying?",
                action=Action.PROBE, label=InputLabel.ON_TOPIC))

    selected = ncert.chapter_of(best)
    concept = ncert.concept_id(best)
    same_topic = chapter == selected.model_dump()
    context = previous if followup else query
    reply, generation = socratic.grounded(text, context, best)
    session.current_concept = concept
    if not same_topic:
        session.target_concept = concept
    session.pending = {"scope": scope, "chapter": selected.model_dump(), "question": context}
    return _finish(db, session, text, TutorReply(
        reply=reply, action=Action.HINT if same_topic else Action.ASK, label=InputLabel.ON_TOPIC,
        concept_id=concept, level=selected.grade, chapter=selected, resource=ncert.resource(best),
        generation=generation))


def handle_message(db: Session, session: SessionRow, text: str, new_topic: bool = False) -> TutorReply:
    text = text.strip()
    if session.course_id == ncert.COURSE_ID:
        return _handle_ncert(db, session, text, new_topic)
    label = guardrails.classify_input(db, text, session.course_id)
    working = step_finder.split_working(text) if session.pending else None
    if label == InputLabel.OFF_TOPIC and working and step_finder.has_arithmetic(working):
        label = InputLabel.ON_TOPIC                # calculation steps for the pending question

    # Answer requests, and off-topic messages (longer than a short answer), never reach the learner model.
    if label == InputLabel.ANSWER_REQUEST or (label == InputLabel.OFF_TOPIC and (
            session.pending is None or len(text.split()) > 4)):
        msg = socratic.REDIRECT_ANSWER if label == InputLabel.ANSWER_REQUEST else socratic.REDIRECT_OFF_TOPIC
        return _finish(db, session, text, TutorReply(reply=msg, action=Action.REDIRECT, label=label))

    found, finding, wrong_without_working = None, None, False
    seen = list((session.pending or {}).get("seen", []))  # question ids asked so far, kept inside `pending`
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
        attempt = step_finder.final_answer(working) if working else text   # working is graded on its last line
        correct = _same(attempt, asked.answer)
        if not correct and working:
            finding = step_finder.find(asked.text, asked.answer, working, asked.hint)
        if finding and finding.source == "arithmetic":
            pass                                   # a slip in the sums is not a misconception
        elif finding and finding.error:
            found = finding.error                  # the model's one-sentence suggestion, unconfirmed
        elif not correct:
            found = misconception.detect(asked.text, attempt, asked.answer, session.learner_id)
        wrong_without_working = not correct and not working
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
        question = _next_question(concept, seen)
        if question:
            seen = [i for i in seen if i != question.id] + [question.id]  # most recent last
    session.pending = {**question.model_dump(), "seen": seen} if question else None

    reply_text = socratic.write(action, concept, question, text)
    if guardrails.leaks_answer(reply_text, question.answer if question else None):
        reply_text = f"Let's think step by step. What do you already know about {concept.name}?"
    if action in (Action.HINT, Action.PROBE):      # same question again: point at the step, or ask to see the steps
        if finding:
            quoted = f" (“{finding.line}”)" if not guardrails.leaks_answer(finding.line, question.answer) else ""
            check = " and check the arithmetic" if finding.source == "arithmetic" else ""
            reply_text = f"Look again at step {finding.step} of your working{quoted}{check}. {reply_text}"
        elif wrong_without_working:
            reply_text = f"{reply_text} {ASK_FOR_WORKING}"

    return _finish(db, session, text, TutorReply(
        reply=reply_text, action=action, label=InputLabel.ON_TOPIC,
        concept_id=concept.id, level=concept.level, resource=_resource(concept), misconception=found,
        wrong_step=finding.step if finding else None))
