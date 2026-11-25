"""One tutoring turn: guardrails -> learner model -> controller -> Socratic model -> guardrails."""
import logging
import re
from difflib import get_close_matches

from fastapi import HTTPException

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionRow, TurnRow
from ..schemas import Action, Concept, InputLabel, Question, Resource, TutorReply
from . import (controller, conversation, course_store, guardrails, learner_model, misconception, ncert, ncert_path,
               retrieval, socratic, step_finder)

log = logging.getLogger(__name__)

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
    r"(?:why|how so|what next|what do you mean|(?:(?:can|could|will) you )?(?:please )?(?:elaborate(?: on (?:that|this|it))?"
    r"|tell me more|say more|explain (?:it |that |this )?(?:more|further)|(?:give|show) me more(?: detail)?|go on)|"
    r"(?:(?:can|could) you )?(?:explain (?:that|this|it)"
    r"(?: problem)?(?: again| in simple words| step by step)?|"
    r"explain (?:in simple words|without the (?:text)?book)|"
    r"(?:give me )?(?:an? |another )?(?:hint|example))|"
    r"(?:can|could|may) i (?:have|get) (?:an?|another) (?:hint|example)|"
    r"(?:(?:can|could) you )?(?:please )?(?:summari[sz]e|recap|sum up)(?: (?:it|that|this|(?:(?:the|this|that) )?(?:topic|lesson|chapter|section)))?(?: please)?|"
    r"(?:(?:can|could) you )?(?:please )?(?:regenera\w*|re-?generate|rephrase|reword|try again|retry|say (?:it|that) again|"
    r"(?:say|explain) (?:it|that|this) (?:differently|another way|in another way))(?: (?:the |that |your )?(?:response|answer|reply|explanation|it|that))?(?: please)?|"
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
_START_LESSON = re.compile(
    r"(?:(?:ok(?:ay)?|alright|sure|yes|yeah|fine|so|well|please)[,.!\s]+)*"
    r"(?:(?:can|could|will) you )?(?:please )?"
    r"(?:teach me|start|begin|go ahead|continue|proceed|"
    r"(?:let['’]?s|let us)(?: (?:start|begin|go|get started|get into|dive into|jump into))?)"
    r"(?: me)?(?: (?:with|into|in|to))?(?: (?:a|any|the|some|this|first|next|our))?"
    r"(?: (?:topic|lesson|chapter|something|it|now|again))?(?: to (?:start|begin) with)?(?: (?:now|please))?[.!?]*",
    re.I)
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
        if not guardrails.numeric_answer(attempt) and not _looks_like_step(text):   # "20!", "20 only", "4x5 is 20 only no"
            attempt = conversation.loose_number(text, question.text) or attempt
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


def _history(db: Session, session: SessionRow, limit: int = 6) -> list[tuple[str, str]]:
    rows = db.execute(select(TurnRow.role, TurnRow.text).where(TurnRow.session_id == session.id)
                      .order_by(TurnRow.id.desc()).limit(limit)).all()
    return [(role, text) for role, text in reversed(rows)]


def _neighbour(db: Session, session: SessionRow, pack, current: Concept, seen: list[str]) -> Concept | None:
    """A related concept (builds on this one, else a prerequisite) that still has an unasked question."""
    related = [c for c in pack.concepts if current.id in c.prerequisites]
    related += [course_store.get_concept(db, session.course_id, p) for p in current.prerequisites]
    return next((c for c in related if c and any(q.id not in seen for q in c.questions)), None)


def _talk(db: Session, session: SessionRow, text: str, asked: Question | None, situation: str, fallback: str,
          pack=None, list_topics: bool = False) -> str:
    """Let the model reply to everyday chat; when the model is unavailable use the fixed fallback.
    The topic list is added only when the learner needs it (`list_topics`: they asked what we cover)."""
    pack = pack or course_store.get_pack(db, session.course_id)
    reply = socratic.chat(asked, text, _history(db, session), situation, topics=_topics(pack))
    if not reply:
        return fallback
    if list_topics and not any(c.name.casefold() in reply.casefold() for c in pack.concepts):
        reply += f" I can help with: {_topics(pack)}."
    return reply


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


def _where_in_pack(db: Session, session: SessionRow, asked: Question | None) -> str:
    """Say which concept we are on, and which one we stepped back from, from the session itself."""
    current = course_store.get_concept(db, session.course_id, session.current_concept) if session.current_concept else None
    if current is None:
        return _menu(course_store.get_pack(db, session.course_id), "We haven't started a topic yet.")
    target = (course_store.get_concept(db, session.course_id, session.target_concept)
              if session.target_concept and session.target_concept != current.id else None)
    where = f"We're on {current.name}" + (f", a step back from {target.name}, which builds on it" if target else "") + "."
    return where + (f" Your question: {asked.text}" if asked else " Ask me anything about it, or pick another topic.")


def _converse_pack(db: Session, session: SessionRow, text: str, asked: Question | None) -> TutorReply | None:
    """Greetings, thanks, yes/next/harder/easier, "I don't know", examples, "what is X?" in a course pack."""
    kind = conversation.classify(text, asked.text if asked else "")   # one model call labels the message
    if kind == "where":
        return _respond(db, session, text, _where_in_pack(db, session, asked))
    apology = ""
    if kind == "repeat":
        kind, apology = ("practice", "Sorry about that! ") if asked else (None, "")
    pack = course_store.get_pack(db, session.course_id)
    named = _named_concept(pack, text) if kind == "explain" else None
    kind = None if kind == "explain" else kind
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
            return tutor(db, session, text, _talk(db, session, text, asked, "Greet them and invite them to continue.",
                         f"Hi! We were working on this one: {asked.text} Give it a try, or say “hint” for a nudge.", pack))
        return tutor(db, session, text, _talk(db, session, text, None, "Greet them and say how you can help.",
                     _menu(pack, "Hi! I'm your tutor. I ask questions, give hints and explain ideas, so you work things out yourself."), pack))
    if kind == "bye":
        return tutor(db, session, text, "Bye! Come back any time. Your progress is saved.")
    if kind == "thanks":
        if asked:
            return tutor(db, session, text, _talk(db, session, text, asked, "They said thanks; reply warmly.",
                         f"You're welcome! Ready when you are.{redo}", pack))
        return tutor(db, session, text, _talk(db, session, text, None, "They said thanks; reply warmly and offer more practice.",
                     _menu(pack, "You're welcome! Want to try something else?"), pack))
    if kind == "menu":
        lead = "I'm your tutor for this course. Ask me to explain an idea, give a hint, or quiz you."
        return tutor(db, session, text, _talk(
            db, session, text, asked, "Explain how you can help: explain ideas, give hints, quiz them, check their steps.",
            _menu(pack, lead) + (f" Right now: {asked.text}" if asked else ""), pack, list_topics=True))
    if kind == "no":
        if asked:
            return tutor(db, session, text, _talk(db, session, text, asked, "They said no; be understanding and offer a hint.",
                         f"That's fine, take your time. Say “hint” if you want a nudge.{redo}", pack))
        return tutor(db, session, text, _talk(db, session, text, None, "They said no; be understanding.",
                     _menu(pack, "No problem. Pick a topic whenever you're ready."), pack))
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
            lead = {"harder": "Let's make it harder.", "easier": "Sure, an easier one.",
                    "any": "Here's a different one."}[want]
            return _present(db, session, text, current, f"{apology}{lead} {question.text}", question, Action.ASK, seen)
        if apology:                                            # complained about repeats: move to a related topic
            other = _neighbour(db, session, pack, current, seen)
            if other:
                q = _next_question(other, seen)
                return _present(db, session, text, other,
                                f"{apology}I've used up my {current.name} questions, so let's try {other.name}, "
                                f"which is closely related. {q.text}", q, Action.ASK, seen)
        if want == "harder":                                   # climb to a concept that builds on this one
            nxt = next((c for c in pack.concepts if current.id in c.prerequisites and c.questions), None)
            if nxt:
                q = _next_question(nxt, seen)
                return _present(db, session, text, nxt, f"Great, let's step up to {nxt.name}, which builds on {current.name}. {q.text}",
                                q, Action.ASK, seen)
            return tutor(db, session, text,
                         f"That's the hardest {current.name} question I have, and you've been through all of them. Nice work! "
                         f"Which would you like next: {_topics(pack)}? Or say “explain {current.name.lower()}” for a recap.")
        if want == "easier":
            prereq = next((course_store.get_concept(db, session.course_id, p) for p in current.prerequisites), None)
            if prereq and prereq.questions:
                q = _next_question(prereq, seen)
                return _present(db, session, text, prereq, f"Let's build up with {prereq.name} first. {q.text}", q, Action.ASK, seen)
            return tutor(db, session, text, f"This is already the most basic {current.name} question I have.{redo or ' Want a hint?'}")
        again = _next_question(current, seen)                  # "another question", but all were used
        if again:
            return _present(db, session, text, current,
                            f"{apology}You've seen all {len(current.questions)} {current.name} question(s) I have, so here's one again: "
                            f"{again.text} Or pick another topic: {_topics(pack)}.", again, Action.ASK, seen)
        return tutor(db, session, text, _menu(pack, f"I have no more {current.name} questions."))
    return None


def _scope_words(state: dict) -> str:
    scope = state.get("scope", {})
    parts = [f"Class {scope['grade']}" if scope.get("grade") else "", (scope.get("subject") or "").replace("maths", "Maths").replace("science", "Science")]
    return "NCERT " + (" ".join(p for p in parts if p) + " " if any(parts) else "") + "textbook"


def _where_are_we(session: SessionRow, state: dict) -> str:
    scope = state.get("scope", {})
    detour = session.stack[-1]["heading"] if session.stack else ""
    chapter = ncert.chapter_title(scope) if scope.get("book_code") else ""
    label = f"Class {scope['grade']} {scope['subject'].title()}" if scope.get("grade") and scope.get("subject") else ""
    place = f"{label} · Chapter {scope['chapter']}{' · ' + chapter if chapter else ''}" if label and scope.get("chapter") else label
    if state.get("chapter_heading"):
        main = (f" The main topic is “{ncert.topic_title(session.stack[0]['heading'])}”, {len(session.stack)} steps up."
                if len(session.stack or []) > 1 else "")
        back = (f" We stepped back here from “{ncert.topic_title(detour)}”.{main} {_return_hint(len(session.stack))}"
                if detour else "")
        return (f"We're on “{ncert.topic_title(state['chapter_heading'])}”" + (f", in {place}" if place else "") + "."
                + (back or " Ask a question about it, say “hint”, or pick another topic from the chapter list."))
    if place:
        return (f"We haven't started a topic yet. This lesson is {place}. "
                f"Pick a topic from the chapter list or ask a question about it.")
    return "We haven't started a topic yet. Pick a topic from the chapter list or ask a question."


def _converse_ncert(db: Session, session: SessionRow, text: str) -> TutorReply | None:
    state = session.pending or {}
    kind = conversation.classify(text, state.get("problem", ""))
    if kind == "where":
        return _respond(db, session, text, _where_are_we(session, state))
    if kind not in ("greeting", "thanks", "bye", "menu"):
        return None
    heading = ncert.topic_title(state["chapter_heading"]) if state.get("chapter_heading") else ""
    carry = f" We were on “{heading}”; carry on, or ask about something new." if heading else ""
    ask = f"Ask me a question from your {_scope_words(state)}, or pick a topic from the chapter list, and we'll work through it step by step."
    reply = {"greeting": f"Hi! {ask}{carry}", "thanks": f"You're welcome!{carry or ' ' + ask}", "bye": "Bye! Come back any time.",
             "menu": f"I explain ideas from the textbook, give hints on exercises and check your steps, without handing out final answers. {ask}"}[kind]
    return _respond(db, session, text, reply)


def _ncert_reply(db: Session, session: SessionRow, text: str, passage: dict, context: str, *,
                 mode: socratic.TeachingMode, followup: bool = False, problem: str = "",
                 action: Action | None = None, lead: str = "", detour: bool = False) -> TutorReply:
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
    if lead:
        reply = lead + reply
    session.current_concept = concept
    if not followup and not detour:                           # a detour keeps the topic we will return to
        session.target_concept = concept
    heading = state.get("chapter_heading") if followup else None
    # passage_id is the chunk this reply is grounded in; topic_passage_id opens the topic named by chapter_heading
    # and is what a step back or a resume works from (a follow-up may be grounded in a chunk of another heading).
    topic_id = (state.get("topic_passage_id") or state.get("passage_id")) if followup and heading else passage["passage_id"]
    session.pending = {"scope": state.get("scope", {}), "chapter": chapter, "question": context,
                       "chapter_heading": heading or passage["heading"], "passage_id": passage["passage_id"],
                       "topic_passage_id": topic_id, "last_message": text, "last_reply": reply, "problem": problem,
                       "stuck": state.get("stuck", 0) if followup else 0}   # a new topic starts its help count again
    return _finish(db, session, text, TutorReply(
        reply=reply, action=action or {"explain": Action.EXPLAIN, "hint": Action.HINT,
                                       "guide": Action.GUIDE, "review": Action.HINT}[mode], label=InputLabel.ON_TOPIC,
        concept_id=concept, level=selected.grade, chapter=selected, resource=ncert.resource(passage),
        generation=generation, wrong_step=slip))


_ABUSE_REPLY = ("I understand this can be frustrating, but please keep it respectful. I'm here to help you "
                "learn. Tell me which part is confusing, or pick a topic, and we'll take it step by step.")


def _start_first_topic(db: Session, session: SessionRow, text: str, scope: dict) -> TutorReply | None:
    """A generic "teach me" has nothing to search for, so begin with the chapter's first topic."""
    if scope.get("chapter") is None:
        return None
    chapters = ncert.catalogue(scope["grade"], scope["subject"])
    topics = next((c.topics for c in chapters
                   if c.book_code == scope.get("book_code") and c.chapter == scope["chapter"]), [])
    passage = ncert.topic_passage(scope, topics[0]) if topics else None
    if not passage:
        return None
    return _ncert_reply(db, session, text, passage, ncert.topic_title(passage["heading"]), mode="explain")


def _current_passage(state: dict) -> dict | None:
    if not (state.get("chapter") and state.get("passage_id")):
        return None
    try:
        return ncert.cited_passage(state["chapter"], state["passage_id"])
    except HTTPException:
        return None


def _topic_passage(state: dict) -> dict | None:
    """The passage that opens the topic on screen (chapter_heading), not just the chunk the last reply used."""
    topic_id = state.get("topic_passage_id")
    if not topic_id or topic_id == state.get("passage_id"):
        return _current_passage(state)
    return _current_passage({**state, "passage_id": topic_id})


def _prerequisites_of(stack: list, passage: dict) -> list[dict]:
    """Topics this one builds on (learning graph first, else embeddings), minus the ones already on the way."""
    try:
        return ncert_path.new_ones(ncert.prerequisites(passage), passage, stack)
    except HTTPException:                                     # corpus unavailable: carry on without a detour
        return []


def _return_hint(depth: int) -> str:
    """How to climb back: one way with a single detour, two (one step, or all the way) with more."""
    if depth > 1:
        return "Say “back to the previous topic” to go up one step, or “back to the main topic” to return straight there."
    return "Say “back to the main topic” when you are ready."


def _step_back(db: Session, session: SessionRow, text: str, state: dict, intro: str,
               deepest: bool = False) -> TutorReply | None:
    """Teach the nearest prerequisite of the current topic and remember where to return to. With `deepest`, follow
    the strongest prerequisite again and again to the most basic topic; every topic passed on the way goes on the
    stack, so climbing back revisits them in order (foundations first)."""
    stack = list(session.stack or [])
    here = _topic_passage(state)
    if here is None:
        return None
    path, came_from, link = [], here, None
    while True:
        options = _prerequisites_of(stack + path, here)
        if not options:
            break
        path.append(ncert_path.entry(here, ncert.chapter_of(here).model_dump()))
        came_from, here, link = here, options[0], options[0]
        if not deepest:
            break
    if not path:
        return None
    session.stack = stack + path
    session.pending = {**state, "stuck": 0}                  # the earlier topic gets its own help before going deeper
    log.info("NCERT step back: %s -> %s, %d level(s) (%s)", path[0]["passage_id"], here["passage_id"], len(path),
             link.get("source", "embedding"))
    subject = "Maths" if here["subject"] == "maths" else "Science"
    title = ncert.topic_title(here["heading"])
    builds_on = (f"where we meet {link['concept']}, which {link['for_concept']} needs" if link.get("concept")
                 else f"which “{ncert.topic_title(came_from['heading'])}” builds on")
    if len(path) > 1:
        passed = ", ".join(f"“{ncert.topic_title(e['heading'])}”" for e in reversed(path[1:]))
        step = (f"Let's start from the foundations with “{title}” (Class {here['grade']} {subject}, "
                f"Chapter {here['chapter']}), {builds_on}. On the way back up we'll pass through {passed}.")
    else:
        step = f"Let's step back to “{title}” (Class {here['grade']} {subject}, Chapter {here['chapter']}), {builds_on}."
    lead = f"{intro} {step} "
    return _ncert_reply(db, session, text, here, title, mode="explain", action=Action.BACKTRACK, lead=lead, detour=True)


def _resume(db: Session, session: SessionRow, text: str, state: dict, to_main: bool = False) -> TutorReply:
    """Climb back to the topic we left for a prerequisite: one level, or with `to_main` straight to the topic the
    detour started from (the whole stack at once)."""
    stack = list(session.stack)
    back = stack[0] if to_main else stack[-1]
    stack = [] if to_main else stack[:-1]
    try:
        passage = ncert.cited_passage(back["chapter"], back["passage_id"])
    except HTTPException:
        passage = None
    session.stack = stack
    if passage is None:
        return _respond(db, session, text, "Pick the topic you were on from the chapter list and we'll carry on.")
    title = ncert.topic_title(passage["heading"])
    session.pending = {**state, "stuck": 0}
    log.info("NCERT advance (%s): back to %s, %d detour(s) left", "to main" if to_main else "resume",
             back["passage_id"], len(stack))
    return _ncert_reply(db, session, text, passage, title, mode="explain", action=Action.ADVANCE,
                        lead=f"Welcome to “{title}”. ", detour=bool(stack))


def _move_on(db: Session, session: SessionRow, text: str, state: dict) -> TutorReply:
    """The learner says they understand: climb back out of a detour, else go to the next topic in the chapter."""
    if session.stack:
        return _resume(db, session, text, state)
    chapter, current = state.get("chapter") or {}, ncert.topic_title(state.get("chapter_heading") or "")
    try:
        topics = next((c.topics for c in ncert.catalogue(chapter["grade"], chapter["subject"])
                       if c.book_code == chapter.get("book_code") and c.chapter == chapter.get("chapter")), []) if chapter else []
        titles = [ncert.topic_title(t) for t in topics]
        later = topics[titles.index(current) + 1:] if current in titles else []
        # The next topic with a teachable passage (a heading can list only filtered-out chunks).
        passage = next((p for p in (ncert.topic_passage(chapter, t) for t in later) if p), None)
    except HTTPException:                                     # corpus unavailable: say so instead of failing the turn
        return _respond(db, session, text, "Great! I can't open the next topic right now. Pick one from the chapter list.")
    if not passage:
        return _respond(db, session, text, "Great! That's the end of this chapter's topics. Pick another topic or ask me a question.")
    session.pending = {**state, "stuck": 0}
    log.info("NCERT advance (next topic): %s -> %s", state.get("topic_passage_id") or state.get("passage_id"),
             passage["passage_id"])
    return _ncert_reply(db, session, text, passage, ncert.topic_title(passage["heading"]), mode="explain",
                        action=Action.ADVANCE, lead="Great! Let's move on. ")


def _practice(db: Session, session: SessionRow, text: str, state: dict, scope: dict,
              passage: dict | None = None) -> TutorReply:
    """The learner wants practice: pose one small question (answer never given) on the open topic, else on the
    lesson's chapter, else ask which topic and remember the request for the reply."""
    passage = passage or _current_passage(state)
    if not passage and scope.get("chapter") is not None:     # the lesson already names a chapter: practise from it
        topics = next((c.topics for c in ncert.catalogue(scope["grade"], scope["subject"])
                       if c.book_code == scope.get("book_code") and c.chapter == scope["chapter"]), [])
        if len(topics) > 1 and ncert.topic_title(topics[0]).casefold().startswith("introduction"):
            topics = topics[1:]                               # an introduction has little to practise on
        passage = ncert.topic_passage(scope, topics[0]) if topics else None
    if not passage:
        session.pending = {**state, "wants_practice": True}
        return _respond(db, session, text, "Happy to practise! Which topic would you like to practise? "
                        "Pick one from the chapter list, or tell me the class, subject or topic.")
    title = ncert.topic_title(passage["heading"])
    question = socratic.chat(
        None, text, _history(db, session),
        f"The student wants to practise “{title}”. Using only this textbook passage, pose ONE short practice question "
        f"for them to solve. Do not give the answer or a worked solution.\nPassage:{ncert.passage_text(passage)[:1200]}",
        topics=title)
    generation = "hosted"
    if not question or "?" not in question:
        question = f"Here's one to try on “{title}”: in your own words, what is the key idea, and where would you use it?"
        generation = "extractive"
    selected = ncert.chapter_of(passage)
    session.current_concept = session.target_concept = ncert.concept_id(passage)
    session.pending = {"scope": state.get("scope", {}), "chapter": selected.model_dump(), "question": title,
                       "chapter_heading": passage["heading"], "passage_id": passage["passage_id"],
                       "last_message": text, "last_reply": question, "problem": question, "stuck": 0}
    return _finish(db, session, text, TutorReply(
        reply=question, action=Action.GUIDE, label=InputLabel.ON_TOPIC, concept_id=session.current_concept,
        level=selected.grade, chapter=selected, resource=ncert.resource(passage), generation=generation))


def _list_prerequisites(db: Session, session: SessionRow, text: str, state: dict) -> TutorReply:
    current = _topic_passage(state)
    options = _prerequisites_of(list(session.stack or []), current) if current else []
    if not options:
        return _respond(db, session, text, "I couldn't find an earlier topic this one clearly builds on. "
                        "Ask about the part that is unclear and we'll work through it.")
    names = "; ".join((f"{o['concept']}, in " if o.get("concept") else "")
                      + f"“{ncert.topic_title(o['heading'])}” (Class {o['grade']}, Chapter {o['chapter']})" for o in options)
    return _respond(db, session, text, f"This topic builds on {names}. Say “go back to the basics” and we'll revise it first.")


def _move_through_lesson(db: Session, session: SessionRow, text: str) -> TutorReply | None:
    """The model reads whether the learner wants to climb back (one step or all the way), move on, revise the
    basics (one step or the most basic topic) or hear the prerequisites (socratic.classify_path). None when it is
    none of these, so the turn carries on as usual."""
    state = session.pending or {}
    move = socratic.classify_path(text, detour=bool(session.stack))
    log.info("Path classifier label: %s", move)
    if move == "main_topic" and session.stack:
        return _resume(db, session, text, state, to_main=True)
    if move in ("resume", "understood") and session.stack:   # inside a detour both mean: climb back one level
        return _resume(db, session, text, state)
    if move in ("resume", "main_topic"):
        return _respond(db, session, text, f"We're already on the main topic, “{ncert.topic_title(state.get('chapter_heading') or '')}”. "
                        "Ask about it, say “hint”, or pick another topic from the chapter list.")
    if move == "understood":
        return _move_on(db, session, text, state)
    if move == "prerequisites":
        return _list_prerequisites(db, session, text, state)
    if move in ("basics", "deepest"):
        return (_step_back(db, session, text, state, "Sure.", deepest=move == "deepest")
                or _list_prerequisites(db, session, text, state))
    return None


_BARE_SUM = re.compile(r"(?i)(?:what(?:'s| is)\s+|calculate\s+|solve\s+|explain\s+|show me\s+|teach me\s+)?[\d\s.,+\-*/x×÷()]+[?=]?")


def _is_exercise(text: str) -> bool:
    """A specific problem to guide, not a concept to explain. The model reads the meaning, so word problems
    ("if we multiply 2, 3 and 5 ...") count; _PROBLEM (regex) is only the fallback when the model is off or unsure."""
    label = socratic.is_problem(text)
    log.info("Problem classifier label: %s", label)
    return bool(_PROBLEM.match(text)) if label is None else label


def _without_clarification(state: dict) -> dict:
    return {k: v for k, v in state.items() if k not in ("clarify", "clarify_query", "clarify_pick")}


def _handle_ncert(db: Session, session: SessionRow, text: str, new_topic: bool,
                  intent: str, scope_label: str, topic_heading: str | None = None) -> TutorReply:
    state = session.pending or {}
    scope = state.get("scope", {})
    if topic_heading is not None:
        passage = ncert.topic_passage(scope, topic_heading)
        if passage is None:
            return _respond(db, session, text, "Choose a lesson topic from this chapter or ask a question about it.")
        session.stack = []                                    # the learner chose a new topic: no detour to return from
        return _ncert_reply(db, session, text, passage, ncert.topic_title(passage["heading"]), mode="explain")

    if new_topic or guardrails.requests_topic_switch(text):
        session.stack = []                                    # a new topic: no detour to return from
    # Moving through the lesson (back to the main topic, basics, prerequisites) is handled in _move_through_lesson.

    # _START_LESSON (regex) is kept above but unused: the model decides below when nothing else places the message.
    if state.get("wants_practice") and scope_label == "unsupported":
        scope_label = "uncertain"                             # we just asked which topic: let retrieval judge the reply
    chapter = None if new_topic else state.get("chapter")
    previous = state.get("question", "")
    legacy_title = (ncert.topic_title(previous.removeprefix("Help me understand ").removesuffix("."))
                    if previous.startswith("Help me understand ") else "")
    active_heading = legacy_title or state.get("chapter_heading") or ""
    numeric = _numeric(text)
    refers_back = bool(_REFERENTIAL.fullmatch(text))
    written_work = bool(_CALCULATION_START.match(text) and step_finder.has_arithmetic(
        text.splitlines()[:step_finder.MAX_LINES]))
    exercise = not refers_back and not written_work and _is_exercise(text)
    review = not exercise and bool(numeric or intent == "answer_attempt" or _ANSWER_PREFIX.match(text) or written_work)
    mentions_topic = _mentions_topic(text, active_heading)
    related = review or intent in _FOLLOWUP_INTENTS or mentions_topic
    followup = bool(chapter and (refers_back or (scope_label != "unsupported" and related)))
    clarification = re.fullmatch(
        r"(?i)(?:(?:(?:class|grade)\s+)?([6-9]|10)(?:\s+(maths|science))?|(maths|science))[.!]?", text)
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
        state = _without_clarification(state)
    elif (unresolved and state.get("clarify_pick") and not new_topic
          and re.fullmatch(r"(?i)\s*(?:yes|yeah|yep|yup|ok(?:ay)?|sure|the first(?: one)?|first(?: one)?|1"
                       r"|(?:it |that )?(?:does ?n[o']?t|doesn't|do ?n[o']?t) matter|no preference|any(?: one)?|either(?: one)?"
                       r"|whichever|whatever|i (?:do ?n[o']?t|don't) (?:know|care)|not sure)[.!]?\s*", text)):
        filters = {**scope, **state["clarify_pick"]}            # "yes" to "Are you asking about A or B?" means the first (best) one
        query, followup = unresolved, False
        state = _without_clarification(state)
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
    if exercise or (query != text and _is_exercise(query)):
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
    helping = followup and not review and (refers_back or mode == "hint" or intent in _HELP_INTENTS)
    stuck = state.get("stuck", 0) + 1 if helping else 0       # help requests in a row: anything else starts again
    state = {**state, "stuck": stuck}
    session.pending = state
    if helping and stuck >= ncert_path.STUCK_LIMIT:           # still lost after help: the gap is probably earlier
        stepped = _step_back(db, session, text, state, "That's okay, this may need an earlier idea first.")
        if stepped:
            return stepped
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

    if (not passages or passages[0]["score"] < ncert.MIN_SCORE) and not followup:
        sums = re.search(r"\d[\d\s.,+\-*/x×÷()]*\d|\.\d+", query)      # bare arithmetic, read from query (not text) so "class 8 maths" can resolve "explain 4 x 5"
        if sums and re.search(r"[+\-*/x×÷]", sums.group(0)):
            kinds = {"+": "addition", "-": "subtraction", "*": "multiplication", "x": "multiplication",
                     "×": "multiplication", "/": "division", "÷": "division"}
            words = " ".join(sorted({v for k, v in kinds.items() if k in sums.group(0)}))
            by_kind = ncert.rank(f"{words} of {'decimals' if re.search(r'\d*\.\d', sums.group(0)) else 'numbers'}",
                                 filters, limit=2, chapters=True)
            if by_kind and by_kind[0]["score"] >= ncert.MIN_SCORE:
                passages = by_kind
                problem = problem or text
    if (not passages or passages[0]["score"] < ncert.MIN_SCORE) and not followup and _BARE_SUM.fullmatch(query.strip())             and re.search(r"[+\-*/x×÷]", query):
        # A plain sum needs no textbook passage: guide it step by step, with the result checked in code.
        value = step_finder.arithmetic_value(re.sub(r"(?i)^(?:what(?:'s| is)|calculate|solve|explain|show me|teach me)\s+", "", query.strip()).rstrip("?="))
        truth = format(float(value), "f").rstrip("0").rstrip(".") if value is not None else ""
        reply = socratic.chat(
            None, text, _history(db, session),
            "This is a plain arithmetic question that is not tied to a textbook passage. Do not give the final result"
            + (f" (it is {truth}; never reveal it)" if truth else "")
            + ". Ask ONE small first step so the student works it out, in one or two short sentences.")
        if not reply or (truth and guardrails.leaks_answer(reply, truth)):
            reply = "Let's work it out together. What is the first thing you would do with these two numbers?"
        return _respond(db, session, text, reply)
    if not passages or passages[0]["score"] < ncert.MIN_SCORE:
        if followup and mentions_topic and state.get("passage_id"):
            passage = ncert.cited_passage(chapter, state["passage_id"])
            if passage:
                return _ncert_reply(db, session, text, passage, previous, mode=mode, followup=True, problem=problem)
        if (chapter and not followup and not new_topic and not unresolved and state.get("passage_id")
                and scope_label != "unsupported"
                and ncert.similarity(query, chapter, state["passage_id"]) >= ncert.FOLLOWUP_MIN_SCORE):
            # Nothing else matched, but the message is close in meaning to the topic on screen: a follow-up by vector.
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
        label = socratic.classify_message(text, topic_open=bool(state.get("passage_id")))   # the model reads what the rules and retrieval could not place
        log.info("Message classifier label: %s", label)
        if label == "understood":
            return _move_on(db, session, text, state)
        if label == "practice":
            return _practice(db, session, text, state, scope)
        if label in ("summarize", "retry"):
            passage = _current_passage(state)
            if passage:
                return _ncert_reply(db, session, text, passage, state.get("question", ""), mode="explain",
                                    followup=True, problem=state.get("problem", ""))
        if label == "abusive":
            return _respond(db, session, text, _ABUSE_REPLY, Action.REDIRECT, InputLabel.OFF_TOPIC)
        # With no label (model unavailable) and no topic yet, begin the first topic rather than dead-end.
        if label in ("start_lesson", None) and not followup and not state.get("chapter_heading"):
            started = _start_first_topic(db, session, text, scope)
            if started:
                return started
        if label == "off_topic":
            return _respond(db, session, text, socratic.REDIRECT_OFF_TOPIC, Action.REDIRECT, InputLabel.OFF_TOPIC)
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
    bare_sum = bool(_BARE_SUM.fullmatch(query.strip()) and re.search(r"[+\-*/x×÷]", query))
    if len(passages) > 1 and best["score"] - passages[1]["score"] < ncert.CHAPTER_MARGIN:
        other = passages[1]
        clarification_prompt = None
        if bare_sum:
            pass                                                # a plain sum needs no class or subject: use the best match
        elif best["grade"] != other["grade"] or best["subject"] != other["subject"]:
            clarification_prompt = (f"This could be Class {best['grade']} {best['subject']} or Class {other['grade']} "
                                    f"{other['subject']}. Which class and subject are you studying?")
        elif (best["book_code"], best["chapter"]) != (other["book_code"], other["chapter"]):
            clarification_prompt = f"Are you asking about {best['heading']} or {other['heading']}?"
        if clarification_prompt:
            pick = {key: best[key] for key in ("grade", "subject", "book_code", "chapter") if best.get(key) is not None}
            session.pending = {**state, "clarify_query": query, "clarify_pick": pick}
            return _respond(db, session, text, clarification_prompt)

    context = previous if followup and not exercise else query
    if state.get("wants_practice") and not followup:         # they asked to practise, then named the topic
        return _practice(db, session, text, state, scope, passage=best)
    return _ncert_reply(db, session, text, best, context, mode=mode, followup=followup, problem=problem)


def _off_topic(db: Session, session: SessionRow, text: str) -> TutorReply:
    pack = course_store.get_pack(db, session.course_id)
    reply = f"That's outside this course, so I can't help with it here. I can help with: {_topics(pack)}. Which would you like?"
    asked = Question(**session.pending) if session.pending and session.pending.get("text") else None
    reply = _talk(db, session, text, asked, "Their message is not about these topics. Say so kindly and steer back.", reply, pack)
    if asked and reply.startswith("That's outside"):
        reply += f" Or carry on with: {asked.text}"
    if not asked and not reply.startswith("That's outside"):   # the model engaged: remember the side thread
        session.pending = {**(session.pending or {}), "chat_thread": True}
    return _respond(db, session, text, reply, Action.REDIRECT, InputLabel.OFF_TOPIC)


def _not_sure(db: Session, session: SessionRow, asked: Question, text: str = "") -> str:
    """A message that fits no pattern: let the model answer it in conversation, else a short fallback that
    does not repeat the question the learner has just seen."""
    reply = socratic.chat(asked, text, _history(db, session), "Answer their message naturally, then steer back to the problem.") if text else None
    if reply:
        return reply
    name = (course_store.get_concept(db, session.course_id, session.current_concept).name
            if session.current_concept else "this topic")
    if "I didn't quite catch" in _last_tutor_text(db, session):   # already said so, with the question: do not repeat it
        return (f"Sorry, I'm still not sure what you mean. We're on {name}. You can type your answer, "
                f"say “hint”, ask me to explain the idea, or name another topic.")
    return (f"I didn't quite catch how that connects to {name}. Your question is: {asked.text} "
            f"You can type your answer, say “hint”, ask me to explain the idea, or name another topic.")


def _next_hint(db: Session, session: SessionRow, asked: Question, text: str) -> str:
    """The question's hint the first time; after that something new, so the learner never gets the same hint twice."""
    hint = asked.hint or "What is the first step you can work out?"
    if guardrails.leaks_answer(hint, asked.answer):
        hint = "Which part of the question can you work out first?"
    if hint not in _last_tutor_text(db, session):
        return hint
    reply = socratic.chat(asked, text, _history(db, session),
                          f"The student wants more help. The hint \"{hint}\" was already given, so give a different, "
                          f"smaller clue or explain the idea in simpler words.")
    if reply:
        return reply
    concept = course_store.get_concept(db, session.course_id, session.current_concept) if session.current_concept else None
    material = concept.materials[0].text if concept and concept.materials else ""
    return (f"Let's look at it another way. {material} Which number does that tell you to start with?"
            if material else "Let's break it into a smaller piece: what is the very first thing the question asks you to find?")


def handle_message(db: Session, session: SessionRow, text: str, new_topic: bool = False,
                   selected_concept: str | None = None, *, topic_heading: str | None = None) -> TutorReply:
    text = text.strip()
    if guardrails.requests_answer(text):
        return _respond(db, session, text, socratic.REDIRECT_ANSWER, Action.REDIRECT, InputLabel.ANSWER_REQUEST)
    # guardrails.is_abusive (word list) is kept but unused: the model labels abuse in _handle_ncert.
    is_ncert = session.course_id == ncert.COURSE_ID
    if is_ncert and topic_heading and text == f"Help me understand {topic_heading}."[:2000]:
        return _handle_ncert(db, session, text, True, "topic_switch", "supported", topic_heading)
    if is_ncert and not new_topic and topic_heading is None and (session.pending or {}).get("passage_id"):
        moved = _move_through_lesson(db, session, text)        # before the chat classifier, which reads "got it" as thanks
        if moved:
            return moved
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
    clarifying = is_ncert and bool((session.pending or {}).get("clarify_query")) and bool(re.fullmatch(r"(?:[6-9]|10)", text))
    if assessment or (is_ncert and active and _numeric(text) and not explicit_switch and not clarifying):
        intent, scope = "answer_attempt", "supported"
    elif active and scope != "unsupported" and guardrails.asks_for_help(text) and not explicit_switch:
        intent, scope = "hint_request", "supported"
    if intent in {"answer_request", "bypass_attempt"}:
        return _respond(db, session, text, socratic.REDIRECT_ANSWER, Action.REDIRECT, InputLabel.ANSWER_REQUEST)
    switch = explicit_switch or (intent == "topic_switch" and not (is_ncert and active and _REFERENTIAL.fullmatch(text)))
    if is_ncert:
        return _handle_ncert(db, session, text, switch, intent, scope, topic_heading)

    if (asked is None and (session.pending or {}).get("chat_thread") and not switch
            and (guardrails.numeric_answer(text) or _looks_like_step(text))):
        # A reply to the model's own side question (e.g. "How many times does 4 go into 5?"): keep talking, do not start a new topic.
        pack = course_store.get_pack(db, session.course_id)
        earlier = _history(db, session, limit=12)
        original = next((t for r, t in earlier if r == "learner" and not _numeric(t) and not _looks_like_step(t)), "")
        expression = re.search(r"\d[\d\s.,+\-*/x×÷()]*\d|\.\d+", original.replace("÷", "/"))
        truth = step_finder.arithmetic_value(expression.group(0)) if expression and original else None
        given = step_finder.arithmetic_value(text)
        if truth is not None and given is not None and given == truth:       # checked by arithmetic, not by the model
            return _respond(db, session, text, f"Yes, {text.strip()} is right. Nicely worked out! "
                            "Want to try another one, or ask about something else?")
        secret = (f" The true final answer is {format(float(truth), 'f').rstrip('0').rstrip('.')} (never reveal it). "
                  "The student's number is NOT that final answer: never say it is correct or right; "
                  "say it is not the final result yet, unless it is plainly a valid intermediate value."
                  if truth is not None else "")
        reply = _talk(db, session, text, None,
                      f"The student's original request was: \"{original[:300]}\". They are working through it step by step "
                      "and their message answers your last step question. Say whether it is right (if wrong, hint at the slip "
                      "without giving the answer), then ask ONE next small step toward the original problem. "
                      f"Stay on that problem; never switch topic. Do not state the final result.{secret}",
                      "Not quite yet. Let's slow down: what is the very first step of the original problem?", pack)
        if truth is not None and (re.search(r"(?i)\b(correct|right|exactly|well done|you've got it)\b", reply)
                                  or guardrails.leaks_answer(reply, format(float(truth), 'f').rstrip('0').rstrip('.'))):
            reply = "Not quite yet. Check your last step again. What is the very first thing the problem asks you to work out?"
        return _respond(db, session, text, reply)

    found, finding, wrong_without_working = None, None, False
    seen =list((session.pending or {}).get("seen", []))  # question ids asked so far, kept inside `pending`
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
        return _respond(db, session, text, _next_hint(db, session, asked, text), Action.HINT)
    elif assessment is None:
        if scope == "unsupported" and intent != "uncertain":
            return _off_topic(db, session, text)
        return _respond(db, session, text, _not_sure(db, session, asked, text))
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
