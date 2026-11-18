"""One tutoring turn: guardrails -> learner model -> controller -> Socratic model -> guardrails."""
from difflib import get_close_matches
import re

from sqlalchemy.orm import Session

from ..db import SessionRow, TurnRow
from ..schemas import Action, Concept, InputLabel, Question, Resource, TutorReply
from . import controller, course_store, guardrails, learner_model, misconception, ncert, retrieval, socratic, step_finder

ASK_FOR_WORKING = "Show your steps, one per line, so I can see where it went wrong."
ASK_FOR_CLARIFICATION = "Are you answering the current question, asking for help, or starting a new topic?"
_HELP_INTENTS = {"doubt", "hint_request", "explanation_request"}
_FOLLOWUP_INTENTS = _HELP_INTENTS | {"answer_attempt"}
_ANSWER_PREFIX = re.compile(r"^(?:my answer is|the answer is|answer:|i (?:think (?:it is|it's)|got|make it))\s*", re.I)
_CALCULATION_START = re.compile(r"^\s*(?:step\s+\d+\s*[:.)-]\s*)?[\d(=+\-]", re.I)
_TOPIC_WORDS_TO_IGNORE = {"about", "does", "explain", "help", "mean", "please", "that", "this", "understand", "what", "with"}
_REFERENTIAL = re.compile(
    r"(?:why|how so|what next|what do you mean|(?:can you )?(?:explain (?:that|this|it)(?: again)?|"
    r"(?:give me )?(?:a |another )?(?:hint|example))|i (?:don['’]t understand(?: why)?|am stuck))[.!? ]*",
    re.I,
)


def _norm(text: str) -> str:
    return text.strip().lower().replace(" ", "").rstrip(".")


def same_answer(attempt: str, answer: str) -> bool:
    """Same text, or the same number written differently (0.5 and 1/2)."""
    if _norm(attempt) == _norm(answer):
        return True
    return (guardrails.numeric_answer(attempt) and guardrails.numeric_answer(answer)
            and misconception.to_value(attempt) == misconception.to_value(answer))


def _assessment_attempt(text: str, question: Question) -> tuple[str, list[str] | None] | None:
    if guardrails.asks_for_help(text):
        return None
    # shortcut: infer numeric answers and recognize explicit text answers, add answer types when packs declare them.
    prefix = _ANSWER_PREFIX.match(text)
    attempt = (text[prefix.end():] if prefix else text).rstrip("?").strip()
    working = step_finder.split_working(attempt) if _CALCULATION_START.match(attempt) else None
    if working and step_finder.has_arithmetic(working):
        attempt = step_finder.final_answer(working)
    else:
        working = None
    if guardrails.numeric_answer(question.answer):
        return (attempt, working) if guardrails.numeric_answer(attempt) else None
    return (attempt, working) if attempt and (prefix or same_answer(attempt, question.answer)) else None


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
    return reply


def _respond(db: Session, session: SessionRow, text: str, reply: str, action: Action = Action.PROBE,
             label: InputLabel = InputLabel.ON_TOPIC) -> TutorReply:
    return _finish(db, session, text, TutorReply(
        reply=reply, action=action, label=label, concept_id=session.current_concept))


def _mentions_topic(text: str, heading: str) -> bool:
    words = set(re.findall(r"[a-z]{4,}", text.casefold())) - _TOPIC_WORDS_TO_IGNORE
    heading_words = set(re.findall(r"[a-z]{4,}", heading.casefold()))
    return any(word in heading_words or (len(word) >= 5 and get_close_matches(word, heading_words, n=1, cutoff=0.88))
               for word in words)


def _ncert_reply(db: Session, session: SessionRow, text: str, passage: dict, context: str, *,
                 new_topic: bool, followup: bool = False) -> TutorReply:
    state = session.pending or {}
    selected = ncert.chapter_of(passage)
    chapter = selected.model_dump()
    concept = ncert.concept_id(passage)
    same_topic = not new_topic and state.get("chapter") == chapter
    model_context = context
    if followup and state.get("last_reply"):
        model_context = f"{context[:180]}\nStudent: {state.get('last_message', '')[:160]}\nTutor: {state['last_reply'][-380:]}"
    reply, generation = socratic.grounded(text, model_context, passage,
                                         previous_reply=state.get("last_reply", "") if followup else "")
    session.current_concept = concept
    if not same_topic:
        session.target_concept = concept
    heading = state.get("chapter_heading") if followup else None
    session.pending = {"scope": state.get("scope", {}), "chapter": chapter, "question": context,
                       "chapter_heading": heading or passage["heading"], "passage_id": passage["passage_id"],
                       "last_message": text, "last_reply": reply}
    return _finish(db, session, text, TutorReply(
        reply=reply, action=Action.HINT if same_topic else Action.ASK, label=InputLabel.ON_TOPIC,
        concept_id=concept, level=selected.grade, chapter=selected, resource=ncert.resource(passage),
        generation=generation))


def _handle_ncert(db: Session, session: SessionRow, text: str, new_topic: bool,
                  intent: str, scope_label: str, topic_heading: str | None = None) -> TutorReply:
    state = session.pending or {}
    scope = state.get("scope", {})
    if topic_heading is not None:
        passage = ncert.topic_passage(scope, topic_heading)
        if passage is None:
            return _respond(db, session, text, "Choose a lesson topic from this chapter or ask a question about it.")
        return _ncert_reply(db, session, text, passage, ncert.topic_title(passage["heading"]), new_topic=True)

    chapter = None if new_topic else state.get("chapter")
    previous = state.get("question", "")
    legacy_title = (ncert.topic_title(previous.removeprefix("Help me understand ").removesuffix("."))
                    if previous.startswith("Help me understand ") else "")
    active_heading = legacy_title or state.get("chapter_heading") or ""
    numeric = guardrails.numeric_answer(text)
    refers_back = numeric or bool(_REFERENTIAL.fullmatch(text))
    followup = bool(chapter and scope_label != "unsupported" and (refers_back or intent in _FOLLOWUP_INTENTS or
                    (intent == "uncertain" and _mentions_topic(text, active_heading))))
    clarification = re.fullmatch(
        r"(?i)(?:(?:class|grade)\s+([6-9]|10)(?:\s+(maths|science))?|(maths|science))[.!]?", text)
    filters, query = scope, text
    unresolved = state.get("clarify_query") or (previous if state.get("clarify") else "")
    if clarification and unresolved and not new_topic:
        grade, subject, subject_only = clarification.groups()
        requested = {"grade": int(grade) if grade else None, "subject": (subject or subject_only or "").lower() or None}
        if any(value and scope.get(key) not in (None, value) for key, value in requested.items()):
            return _respond(db, session, text, "That class or subject is outside this session's selection.",
                            Action.REDIRECT, InputLabel.OFF_TOPIC)
        filters = {**scope, **{key: value for key, value in requested.items() if value}}
        query, followup = unresolved, False
    elif unresolved and intent == "clarification_reply" and not new_topic:
        query, followup = f"{unresolved}\nClarification: {text}", False
    elif not new_topic and not followup:
        if scope_label == "unsupported":
            return _respond(db, session, text, socratic.REDIRECT_OFF_TOPIC, Action.REDIRECT, InputLabel.OFF_TOPIC)
        if numeric or clarification or intent == "clarification_reply":
            return _respond(db, session, text, "Which textbook topic or question are you working on?")
        if intent == "other":
            return _respond(db, session, text, "What would you like to work on next?")

    if followup and state.get("passage_id") and (refers_back or intent == "answer_attempt"):
        passage = ncert.cited_passage(chapter, state["passage_id"])
        if passage:
            return _ncert_reply(db, session, text, passage, previous, new_topic=False, followup=True)
    if followup:
        passages = ncert.rank(f"{legacy_title or previous}\n{query}", chapter, limit=1)
    else:
        passages = ncert.rank(query, filters, limit=2, chapters=True)

    if not passages or passages[0]["score"] < ncert.MIN_SCORE:
        if new_topic and any(scope.get(key) for key in ("grade", "subject")):
            outside = ncert.rank(query, {}, limit=2, chapters=True)
            if (outside and outside[0]["score"] >= ncert.MIN_SCORE
                    and any(scope.get(key) and scope[key] != outside[0][key] for key in ("grade", "subject"))
                    and (len(outside) == 1 or outside[0]["score"] - outside[1]["score"] >= ncert.CHAPTER_MARGIN)):
                return _respond(db, session, text, "That topic is outside this session's class or subject.",
                                Action.REDIRECT, InputLabel.OFF_TOPIC)
        if not followup:
            session.pending = {**state, "clarify_query": query}
        if followup:
            message = "Which part of the current textbook topic are you working on?"
        elif scope.get("chapter") is not None:
            message = "I couldn't find a matching passage in this chapter. Could you rephrase or choose a chapter topic?"
        else:
            message = "I couldn't find a matching NCERT passage. What class, subject or textbook topic is this about?"
        if scope_label == "unsupported":
            return _respond(db, session, text, socratic.REDIRECT_OFF_TOPIC, Action.REDIRECT, InputLabel.OFF_TOPIC)
        return _respond(db, session, text, message)

    best = passages[0]
    if len(passages) > 1 and best["score"] - passages[1]["score"] < ncert.CHAPTER_MARGIN:
        other = passages[1]
        clarification_prompt = None
        if best["grade"] != other["grade"] or best["subject"] != other["subject"]:
            clarification_prompt = (f"This could be Class {best['grade']} {best['subject']} or Class {other['grade']} "
                                    f"{other['subject']}. Which class and subject are you studying?")
        elif (best["book_code"], best["chapter"]) != (other["book_code"], other["chapter"]):
            clarification_prompt = f"Are you asking about {best['heading']} or {other['heading']}?"
        if clarification_prompt:
            session.pending = {**state, "clarify_query": query}
            return _respond(db, session, text, clarification_prompt)

    context = previous if followup else query
    return _ncert_reply(db, session, text, best, context, new_topic=new_topic, followup=followup)


def handle_message(db: Session, session: SessionRow, text: str, new_topic: bool = False,
                   selected_concept: str | None = None, *, topic_heading: str | None = None) -> TutorReply:
    text = text.strip()
    if guardrails.requests_answer(text):
        return _respond(db, session, text, socratic.REDIRECT_ANSWER, Action.REDIRECT, InputLabel.ANSWER_REQUEST)
    is_ncert = session.course_id == ncert.COURSE_ID
    if is_ncert and topic_heading and text == f"Help me understand {topic_heading}."[:2000]:
        return _handle_ncert(db, session, text, True, "topic_switch", "supported", topic_heading)
    asked = Question(**session.pending) if session.pending and not is_ncert else None
    intent, scope = guardrails.classify_input(db, session, text, asked)
    explicit_switch = (new_topic or selected_concept is not None or (is_ncert and topic_heading is not None)
                       or guardrails.requests_topic_switch(text))
    assessment = _assessment_attempt(text, asked) if asked and not explicit_switch else None
    active = (session.pending or {}).get("chapter") if is_ncert else asked
    if assessment or (is_ncert and active and guardrails.numeric_answer(text) and not explicit_switch):
        intent, scope = "answer_attempt", "supported"
    elif active and scope != "unsupported" and guardrails.asks_for_help(text) and not explicit_switch:
        intent, scope = "hint_request", "supported"
    if intent in {"answer_request", "bypass_attempt"}:
        return _respond(db, session, text, socratic.REDIRECT_ANSWER, Action.REDIRECT, InputLabel.ANSWER_REQUEST)
    switch = explicit_switch or intent == "topic_switch"
    if is_ncert:
        return _handle_ncert(db, session, text, switch, intent, scope, topic_heading)

    found, finding, wrong_without_working = None, None, False
    seen = list((session.pending or {}).get("seen", []))  # question ids asked so far, kept inside `pending`
    if switch or (asked is None and scope != "unsupported" and intent != "other"):
        concept_id = (course_store.get_concept(db, session.course_id, selected_concept).id
                      if selected_concept is not None else retrieval.best_concept(db, session.course_id, text))
        if concept_id is None:
            if scope == "unsupported" or (asked is None and not switch and not guardrails.asks_for_help(text)
                                          and not guardrails.numeric_answer(text)):
                return _respond(db, session, text, socratic.REDIRECT_OFF_TOPIC, Action.REDIRECT, InputLabel.OFF_TOPIC)
            return _respond(db, session, text, "Which topic in this course would you like to work on?")
        session.target_concept = session.current_concept = concept_id
        session.stack, session.tries = [], 0
        action = Action.ASK
    elif asked is None:
        if scope == "unsupported":
            return _respond(db, session, text, socratic.REDIRECT_OFF_TOPIC, Action.REDIRECT, InputLabel.OFF_TOPIC)
        return _respond(db, session, text, "What would you like to work on?")
    elif assessment is None and intent in _HELP_INTENTS and scope != "unsupported":
        hint = asked.hint or "What is the first step you can work out?"
        if guardrails.leaks_answer(hint, asked.answer):
            hint = "Which part of the question can you work out first?"
        return _respond(db, session, text, hint, Action.HINT)
    elif assessment is None:
        if scope == "unsupported" and intent != "uncertain":
            return _respond(db, session, text, socratic.REDIRECT_OFF_TOPIC, Action.REDIRECT, InputLabel.OFF_TOPIC)
        reply = "What would you like to work on next?" if intent == "other" else ASK_FOR_CLARIFICATION
        return _respond(db, session, text, reply)
    else:
        attempt, working = assessment
        correct = same_answer(attempt, asked.answer)
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
