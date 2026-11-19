"""One tutoring turn: guardrails -> learner model -> controller -> Socratic model -> guardrails."""
import re
from difflib import get_close_matches

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionRow, TurnRow
from ..schemas import Action, Concept, InputLabel, Question, Resource, TutorReply
from . import (controller, conversation, course_store, guardrails, learner_model, misconception, ncert, retrieval,
               socratic, step_finder)

ASK_FOR_WORKING = "Show your steps, one per line, so I can see where it went wrong."
_HELP_INTENTS = {"doubt", "hint_request", "explanation_request"}
_FOLLOWUP_INTENTS = _HELP_INTENTS | {"answer_attempt"}
_ANSWER_PREFIX = re.compile(
    r"^(?:my answer is|the answer is|answer:|i (?:think (?:it is|it's|its)|got|make it)|it(?:['’]s| is)|is it)\s*", re.I)
_QUESTION_START = re.compile(r"(?:what|why|how|who|when|where|which|can|could|is|are|do|does)\b", re.I)
_VALUE = r"(?:[a-zA-Z]\s*=\s*)?[-+]?\d+(?:\.\d+)?(?:/\d+)?"
_VALUES_ANSWER = re.compile(rf"{_VALUE}(?:\s*(?:,|or|and)\s*{_VALUE})*[.!]?")
_STEP_WORDS = re.compile(r"=|\bmeans?\b|\bequals?\b|\bbecause\b|%|/|\bdivid|\bmultipl", re.I)
_CALCULATION_START = re.compile(r"^\s*(?:step\s+\d+\s*[:.)-]\s*)?[\d(=+\-]", re.I)
_TOPIC_WORDS_TO_IGNORE = {"about", "does", "explain", "help", "mean", "please", "that", "this", "understand", "what", "with"}
_REFERENTIAL = re.compile(
    r"(?:why|how so|what next|what do you mean|(?:(?:can|could) you )?(?:explain (?:that|this|it)"
    r"(?: problem)?(?: again| in simple words| step by step)?|"
    r"explain (?:in simple words|without the (?:text)?book)|"
    r"(?:give me )?(?:an? |another )?(?:hint|example))|"
    r"(?:can|could|may) i (?:have|get) (?:an?|another) (?:hint|example)|"
    r"i (?:(?:still )?don['’]t (?:understand(?: why)?|have the (?:text)?book)|am stuck|"
    r"(?:am not|['’]m not) referring to (?:the )?(?:text)?book))[.!? ]*",
    re.I,
)
_HINT = re.compile(r"\b(?:hint|clue)\b", re.I)
_PROBLEM = re.compile(
    r"^(?:(?:please |help me )?(?:solve|calculate|simplify|evaluate|find|prove|work out|determine)\b|"
    r"how (?:do|should|would|can) (?:i|we|you)\b|(?:what is\s+)?[-+]?\d[^?\n]*(?:[+*/×÷−%-]|\bx\b))",
    re.I,
)
_EXPLAIN = re.compile(
    r"^(?:(?:can|could) you )?(?:how (?:do|does|can|is)|what (?:is|are|does|do you mean)|"
    r"why|define|explain|teach me|help me understand)\b",
    re.I,
)
_PLAIN_CALCULATION = re.compile(
    r"(?:(?:what is|calculate|evaluate|work out|solve|simplify)\s+)?"
    r"([-+]?\d[\d .()+*/×÷xX−-]*[+*/×÷xX−-][\d .()+*/×÷xX−-]+?)[?.]?\s*",
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
    wrapped = conversation.unwrap_answer(text)            # "is 10 correct?" -> "10"
    prefix = None if wrapped else _ANSWER_PREFIX.match(text)
    attempt = (wrapped or (text[prefix.end():] if prefix else text)).rstrip("?").strip()
    if guardrails.numeric_answer(question.answer):         # "ten" -> "10"
        attempt = conversation.number_from_words(attempt) or attempt
    working = step_finder.split_working(attempt) if _CALCULATION_START.match(attempt) else None
    if working and step_finder.has_arithmetic(working):
        attempt = step_finder.final_answer(working)
    else:
        working = None
    if guardrails.numeric_answer(question.answer):
        return (attempt, working) if guardrails.numeric_answer(attempt) else None
    return (attempt, working) if attempt and (prefix or wrapped or same_answer(attempt, question.answer)) else None


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


def _numeric(text: str) -> bool:
    """A bare number, or values such as "x = 2" or "2, 3" (NCERT exercises often have more than one answer)."""
    return guardrails.numeric_answer(text) or bool(_VALUES_ANSWER.fullmatch(text.strip()))


def _looks_like_step(text: str) -> bool:
    """One line of working such as "20% means 20/100": a step, not a question and not a final answer."""
    return (len(text) <= 200 and "?" not in text and bool(re.search(r"\d", text)) and bool(_STEP_WORDS.search(text))
            and not _QUESTION_START.match(text.strip()))


def _last_tutor_text(db: Session, session: SessionRow) -> str:
    return db.execute(select(TurnRow.text).where(TurnRow.session_id == session.id, TurnRow.role == "tutor")
                      .order_by(TurnRow.id.desc()).limit(1)).scalar() or ""


def _topics(pack) -> str:
    return ", ".join(c.name for c in pack.concepts)


def _menu(pack, lead: str) -> str:
    return (f"{lead} I can help with: {_topics(pack)}. "
            f"Say, for example, “Teach me {pack.concepts[0].name}”, or ask “What is {pack.concepts[-1].name.lower()}?”").strip()


def _named_concept(pack, text: str) -> Concept | None:
    """A concept the learner names in their message ("what is a percentage?" -> percentages)."""
    t = text.casefold()
    return next((c for c in pack.concepts
                 if c.name.casefold() in t or c.id in t or (c.id.endswith("s") and c.id[:-1] in t)), None)


def _present(db: Session, session: SessionRow, text: str, concept: Concept, reply: str, question: Question | None,
             action: Action, seen: list[str]) -> TutorReply:
    """Send a reply that hands out `question` (or none) and save it as the pending question."""
    if session.current_concept != concept.id:                 # a new concept starts a fresh path
        session.target_concept = session.current_concept = concept.id
        session.stack, session.tries = [], 0
    if question and guardrails.leaks_answer(reply, question.answer):
        reply = f"Let's look at {concept.name} together. Here's a question: {question.text}"
    if question:
        session.pending = {**question.model_dump(), "seen": [i for i in seen if i != question.id] + [question.id]}
    return _finish(db, session, text, TutorReply(
        reply=reply, action=action, label=InputLabel.ON_TOPIC, concept_id=concept.id, level=concept.level,
        resource=_resource(concept)))


def _pick(concept: Concept, seen: list[str], want: str, current: Question | None) -> Question | None:
    """An unseen question: any, easier or harder than the one the learner is on."""
    unseen = [q for q in concept.questions if q.id not in seen]
    level = current.difficulty if current else None
    if want == "harder" and level is not None:
        unseen = [q for q in unseen if q.difficulty > level]
    elif want == "easier" and level is not None:
        unseen = [q for q in unseen if q.difficulty < level]
    if not unseen:
        return None
    return max(unseen, key=lambda q: q.difficulty) if want == "easier" else min(unseen, key=lambda q: q.difficulty)


def _converse_pack(db: Session, session: SessionRow, text: str, asked: Question | None) -> TutorReply | None:
    """Greetings, thanks, yes/next/harder/easier, "I don't know", examples, "what is X?" in a course pack."""
    kind = conversation.classify(text)
    pack = course_store.get_pack(db, session.course_id)
    named = _named_concept(pack, text) if conversation.explain_request(text) else None
    if kind is None and named is None:
        return None
    seen = list((session.pending or {}).get("seen", []))
    current = course_store.get_concept(db, session.course_id, session.current_concept) if session.current_concept else None
    tutor = _respond   # shorthand: plain text reply, no new question
    redo = f" Here's the question again: {asked.text}" if asked else ""

    if named is not None:                                      # "what is a percentage?" -> teach, then ask
        material = named.materials[0].text if named.materials else f"{named.name} is part of this course."
        question = asked if asked and named.id == session.current_concept else _next_question(named, seen)
        reply = f"{material} Now you try: {question.text}" if question else material
        return _present(db, session, text, named, reply, question, Action.EXPLAIN, seen)

    if kind == "greeting":
        if asked:
            return tutor(db, session, text, f"Hi! We were working on this one: {asked.text} Give it a try, or say “hint” for a nudge.")
        return tutor(db, session, text, _menu(pack, "Hi! I'm your tutor. I ask questions, give hints and explain ideas, so you work things out yourself."))
    if kind == "bye":
        return tutor(db, session, text, "Bye! Come back any time. Your progress is saved.")
    if kind == "thanks":
        if asked:
            return tutor(db, session, text, f"You're welcome! Ready when you are.{redo}")
        return tutor(db, session, text, _menu(pack, "You're welcome! Want to try something else?"))
    if kind == "menu":
        lead = "I'm your tutor for this course. Ask me to explain an idea, give a hint, or quiz you."
        return tutor(db, session, text, _menu(pack, lead) + (f" Right now: {asked.text}" if asked else ""))
    if kind == "no":
        if asked:
            return tutor(db, session, text, f"That's fine, take your time. Say “hint” if you want a nudge.{redo}")
        return tutor(db, session, text, _menu(pack, "No problem. Pick a topic whenever you're ready."))
    if kind == "idk":
        if not asked or not current:
            return tutor(db, session, text, _menu(pack, "That's okay, let's find a starting point."))
        said_hint = bool(asked.hint) and asked.hint in _last_tutor_text(db, session)
        if said_hint and current.materials:                    # second time: explain instead of repeating the hint
            return _present(db, session, text, current, f"Let's go back to the idea. {current.materials[0].text} Try the question again: {asked.text}",
                            asked, Action.HINT, seen)
        hint = asked.hint if asked.hint and not guardrails.leaks_answer(asked.hint, asked.answer) else "What is the first step you can work out?"
        return tutor(db, session, text, f"No worries, that's how learning works. Hint: {hint}{redo}", Action.HINT)
    if kind == "example":
        if not current:
            return tutor(db, session, text, _menu(pack, "Happy to give an example."))
        material = current.materials[0].text if current.materials else ""
        question = asked or _next_question(current, seen)
        reply = f"Here's the idea: {material}" + (f" Now try this: {question.text}" if question else "")
        return _present(db, session, text, current, reply, question, Action.EXPLAIN, seen)
    if kind == "yes" and asked:
        return tutor(db, session, text, f"Great, let's go.{redo}")
    if kind in ("harder", "easier", "practice") or (kind == "yes" and not asked):
        if kind == "yes" and "harder" not in _last_tutor_text(db, session):
            return tutor(db, session, text, _menu(pack, "Great!") if not current else
                         f"Great! Say “harder”, “easier” or “another question”, or pick a topic. I can help with: {_topics(pack)}.")
        if not current:
            return tutor(db, session, text, _menu(pack, "Let's practise."))
        want = "harder" if kind in ("harder", "yes") else "easier" if kind == "easier" else "any"
        now = asked or next((q for q in current.questions if seen and q.id == seen[-1]), None)
        question = _pick(current, seen, want, now)
        if question:
            lead = {"harder": "Let's make it harder.", "easier": "Sure, an easier one.", "any": "Here's another one."}[want]
            return _present(db, session, text, current, f"{lead} {question.text}", question, Action.ASK, seen)
        if want == "harder":                                   # climb to a concept that builds on this one
            nxt = next((c for c in pack.concepts if current.id in c.prerequisites and c.questions), None)
            if nxt:
                q = _next_question(nxt, seen)
                return _present(db, session, text, nxt, f"Great, let's step up to {nxt.name}, which builds on {current.name}. {q.text}",
                                q, Action.ASK, seen)
            return tutor(db, session, text, _menu(pack, f"You've worked through everything I have on {current.name}."))
        if want == "easier":
            prereq = next((course_store.get_concept(db, session.course_id, p) for p in current.prerequisites), None)
            if prereq and prereq.questions:
                q = _next_question(prereq, seen)
                return _present(db, session, text, prereq, f"Let's build up with {prereq.name} first. {q.text}", q, Action.ASK, seen)
            return tutor(db, session, text, f"This is already the most basic {current.name} question I have.{redo or ' Want a hint?'}")
        again = _next_question(current, seen)                  # "another question", but all were used
        if again:
            return _present(db, session, text, current,
                            f"You've seen all {len(current.questions)} {current.name} question(s) I have, so here's one again: "
                            f"{again.text} Or pick another topic: {_topics(pack)}.", again, Action.ASK, seen)
        return tutor(db, session, text, _menu(pack, f"I have no more {current.name} questions."))
    return None


def _scope_words(state: dict) -> str:
    scope = state.get("scope", {})
    parts = [f"Class {scope['grade']}" if scope.get("grade") else "", (scope.get("subject") or "").replace("maths", "Maths").replace("science", "Science")]
    return "NCERT " + (" ".join(p for p in parts if p) + " " if any(parts) else "") + "textbook"


def _converse_ncert(db: Session, session: SessionRow, text: str) -> TutorReply | None:
    kind = conversation.classify(text)
    if kind not in ("greeting", "thanks", "bye", "menu"):
        return None
    state = session.pending or {}
    heading = ncert.topic_title(state["chapter_heading"]) if state.get("chapter_heading") else ""
    carry = f" We were on “{heading}”; carry on, or ask about something new." if heading else ""
    ask = f"Ask me a question from your {_scope_words(state)}, or pick a topic from the chapter list, and we'll work through it step by step."
    reply = {"greeting": f"Hi! {ask}{carry}", "thanks": f"You're welcome!{carry or ' ' + ask}", "bye": "Bye! Come back any time.",
             "menu": f"I explain ideas from the textbook, give hints on exercises and check your steps, without handing out final answers. {ask}"}[kind]
    return _respond(db, session, text, reply)


def _ncert_reply(db: Session, session: SessionRow, text: str, passage: dict, context: str, *,
                 mode: socratic.TeachingMode, followup: bool = False, problem: str = "") -> TutorReply:
    state = session.pending or {}
    selected = ncert.chapter_of(passage)
    chapter = selected.model_dump()
    concept = ncert.concept_id(passage)
    model_context = f"Class {selected.grade} {selected.subject}. Topic: {ncert.topic_title(passage['heading'])}."
    if problem:
        model_context += f"\nCurrent exercise: {problem[:320]}"
    elif context:
        model_context += f"\nLearning goal: {context[:170]}"
    if followup and state.get("last_reply"):
        model_context += f"\nStudent: {state.get('last_message', '')[:120]}\nTutor: {state['last_reply'][-240:]}"
    working = step_finder.split_working(text) if mode == "review" else None
    slip = step_finder.arithmetic_slip(working) if working else None
    if slip:
        reply = f"Recheck the arithmetic in step {slip}. Evaluate both sides separately. Do they have the same value?"
        generation = "extractive"
    else:
        arithmetic = _PLAIN_CALCULATION.fullmatch(problem)
        reply, generation = socratic.grounded(
            text, model_context, passage, mode=mode, problem=problem, calculation=arithmetic[1] if arithmetic else "",
            previous_reply=state.get("last_reply", "") if followup else "",
        )
    session.current_concept = concept
    if not followup:
        session.target_concept = concept
    heading = state.get("chapter_heading") if followup else None
    session.pending = {"scope": state.get("scope", {}), "chapter": chapter, "question": context,
                       "chapter_heading": heading or passage["heading"], "passage_id": passage["passage_id"],
                       "last_message": text, "last_reply": reply, "problem": problem}
    return _finish(db, session, text, TutorReply(
        reply=reply, action={"explain": Action.EXPLAIN, "hint": Action.HINT,
                             "guide": Action.GUIDE, "review": Action.HINT}[mode], label=InputLabel.ON_TOPIC,
        concept_id=concept, level=selected.grade, chapter=selected, resource=ncert.resource(passage),
        generation=generation, wrong_step=slip))


def _handle_ncert(db: Session, session: SessionRow, text: str, new_topic: bool,
                  intent: str, scope_label: str, topic_heading: str | None = None) -> TutorReply:
    state = session.pending or {}
    scope = state.get("scope", {})
    if topic_heading is not None:
        passage = ncert.topic_passage(scope, topic_heading)
        if passage is None:
            return _respond(db, session, text, "Choose a lesson topic from this chapter or ask a question about it.")
        return _ncert_reply(db, session, text, passage, ncert.topic_title(passage["heading"]), mode="explain")

    chapter = None if new_topic else state.get("chapter")
    previous = state.get("question", "")
    legacy_title = (ncert.topic_title(previous.removeprefix("Help me understand ").removesuffix("."))
                    if previous.startswith("Help me understand ") else "")
    active_heading = legacy_title or state.get("chapter_heading") or ""
    numeric = _numeric(text)
    refers_back = bool(_REFERENTIAL.fullmatch(text))
    written_work = bool(_CALCULATION_START.match(text) and step_finder.has_arithmetic(
        text.splitlines()[:step_finder.MAX_LINES]))
    exercise = not refers_back and not written_work and bool(_PROBLEM.match(text))
    review = not exercise and bool(numeric or intent == "answer_attempt" or _ANSWER_PREFIX.match(text) or written_work)
    mentions_topic = _mentions_topic(text, active_heading)
    related = review or intent in _FOLLOWUP_INTENTS or mentions_topic
    followup = bool(chapter and (refers_back or (scope_label != "unsupported" and related)))
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

    problem = ""
    if followup:
        problem = state.get("problem", previous if _PROBLEM.match(previous) else "")
    if exercise or (query != text and _PROBLEM.match(query)):
        problem = query
    mode: socratic.TeachingMode = "explain"
    if followup and review:
        mode = "review"
    elif _HINT.search(query) or (refers_back and intent in {"doubt", "hint_request"} and not _EXPLAIN.match(query)):
        mode = "hint"
    elif problem:
        if _EXPLAIN.match(query) and not exercise and not refers_back:
            problem = ""
        else:
            mode = "guide"
    if followup and (refers_back or review):
        passage_id = state.get("passage_id")
        passage = ncert.cited_passage(chapter, passage_id) if passage_id else None
        if not passage and state.get("chapter_heading"):
            passage = ncert.topic_passage(chapter, state["chapter_heading"])
        if passage:
            return _ncert_reply(db, session, text, passage, previous, mode=mode, followup=True, problem=problem)
    if followup:
        passages = ncert.rank(f"{legacy_title or previous}\n{query}", chapter, limit=1)
    else:
        passages = ncert.rank(query, filters, limit=2, chapters=True)

    if not passages or passages[0]["score"] < ncert.MIN_SCORE:
        if followup and mentions_topic and state.get("passage_id"):
            passage = ncert.cited_passage(chapter, state["passage_id"])
            if passage:
                return _ncert_reply(db, session, text, passage, previous, mode=mode, followup=True, problem=problem)
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

    context = previous if followup and not exercise else query
    return _ncert_reply(db, session, text, best, context, mode=mode, followup=followup, problem=problem)


def _off_topic(db: Session, session: SessionRow, text: str) -> TutorReply:
    pack = course_store.get_pack(db, session.course_id)
    reply = f"That's outside this course, so I can't help with it here. I can help with: {_topics(pack)}. Which would you like?"
    if session.pending and session.pending.get("text"):
        reply += f" Or carry on with: {session.pending['text']}"
    return _respond(db, session, text, reply, Action.REDIRECT, InputLabel.OFF_TOPIC)


def _not_sure(db: Session, session: SessionRow, asked: Question) -> str:
    """When a message fits no pattern: say so, and list what the learner can do next."""
    name = (course_store.get_concept(db, session.course_id, session.current_concept).name
            if session.current_concept else "this topic")
    return (f"I didn't quite catch how that connects to {name}. Your question is: {asked.text} "
            f"You can type your answer, say “hint”, ask me to explain the idea, or name another topic.")


def handle_message(db: Session, session: SessionRow, text: str, new_topic: bool = False,
                   selected_concept: str | None = None, *, topic_heading: str | None = None) -> TutorReply:
    text = text.strip()
    if guardrails.requests_answer(text):
        return _respond(db, session, text, socratic.REDIRECT_ANSWER, Action.REDIRECT, InputLabel.ANSWER_REQUEST)
    is_ncert = session.course_id == ncert.COURSE_ID
    if is_ncert and topic_heading and text == f"Help me understand {topic_heading}."[:2000]:
        return _handle_ncert(db, session, text, True, "topic_switch", "supported", topic_heading)
    asked = Question(**session.pending) if session.pending and session.pending.get("text") and not is_ncert else None
    intent, scope = guardrails.classify_input(db, session, text, asked)
    explicit_switch = (new_topic or selected_concept is not None or (is_ncert and topic_heading is not None)
                       or guardrails.requests_topic_switch(text))
    assessment = _assessment_attempt(text, asked) if asked and not explicit_switch else None
    if not assessment and not explicit_switch:                # everyday conversation first: the classifier is unsure on these
        quick = _converse_ncert(db, session, text) if is_ncert else _converse_pack(db, session, text, asked)
        if quick:
            return quick
        if asked and not is_ncert and _looks_like_step(text):
            return _respond(db, session, text, "Thanks for showing your thinking. Keep going with that step: "
                            "what number do you end up with?")
    active = (session.pending or {}).get("chapter") if is_ncert else asked
    if assessment or (is_ncert and active and _numeric(text) and not explicit_switch):
        intent, scope = "answer_attempt", "supported"
    elif active and scope != "unsupported" and guardrails.asks_for_help(text) and not explicit_switch:
        intent, scope = "hint_request", "supported"
    if intent in {"answer_request", "bypass_attempt"}:
        return _respond(db, session, text, socratic.REDIRECT_ANSWER, Action.REDIRECT, InputLabel.ANSWER_REQUEST)
    switch = explicit_switch or (intent == "topic_switch" and not (is_ncert and active and _REFERENTIAL.fullmatch(text)))
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
                return _off_topic(db, session, text)
            return _respond(db, session, text, _menu(course_store.get_pack(db, session.course_id), "Which topic would you like to work on?"))
        session.target_concept = session.current_concept = concept_id
        session.stack, session.tries = [], 0
        action = Action.ASK
    elif asked is None:
        if scope == "unsupported":
            return _off_topic(db, session, text)
        return _respond(db, session, text, _menu(course_store.get_pack(db, session.course_id), "What would you like to work on?"))
    elif assessment is None and intent in _HELP_INTENTS and scope != "unsupported":
        hint = asked.hint or "What is the first step you can work out?"
        if guardrails.leaks_answer(hint, asked.answer):
            hint = "Which part of the question can you work out first?"
        return _respond(db, session, text, hint, Action.HINT)
    elif assessment is None:
        if scope == "unsupported" and intent != "uncertain":
            return _off_topic(db, session, text)
        return _respond(db, session, text, _not_sure(db, session, asked))
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
    session.pending = {**question.model_dump(), "seen": seen} if question else {"seen": seen}   # after DONE keep only the history

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
