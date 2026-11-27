"""Conversation memory for the NCERT reply writer: recent turns (short-term) and a progress summary written by
code (long-term), with TUTOR_MEMORY=off restoring the single previous exchange."""
import json

import pytest
from sqlalchemy import select

from app.db import MemoryItemRow, SessionLocal, SessionRow, TurnRow
from app.services import learner_model, llm, memory, ncert, socratic

@pytest.fixture(autouse=True)
def memory_on(monkeypatch):
    monkeypatch.setenv("TUTOR_MEMORY", "on")             # whatever the shell says; the off test sets it again


CHAPTER = {"grade": 10, "subject": "science", "book_code": "jesc1", "chapter": 2}


def _passage(heading):
    return {**CHAPTER, "passage_id": f"p-{heading}", "heading": heading, "physical_page": 30,
            "source_url": "https://ncert.nic.in/textbook/pdf/jesc102.pdf", "score": 0.8,
            "content": f"{heading} is an idea in this chapter. Salts form when an acid reacts with a base."}


def _lesson(ncert_client, monkeypatch):
    """A session on the salts chapter whose reply writer records the context it is given."""
    contexts = []
    monkeypatch.setattr(ncert, "topic_passage", lambda chapter, heading: _passage(heading))
    monkeypatch.setattr(ncert, "cited_passage", lambda chapter, passage_id: _passage(passage_id.removeprefix("p-")))
    monkeypatch.setattr(ncert, "rank", lambda *args, **kwargs: [_passage("Salts")])

    def hosted(text, context, evidence, mode):
        contexts.append(context)
        return f"Reply {len(contexts)}: think about what an acid and a base make. What do you get?"

    monkeypatch.setattr(socratic, "_hosted", hosted)
    created = ncert_client.post("/sessions", json={"learner_id": "memory-test", "course_id": "ncert", "chapter": CHAPTER})
    sid = created.json()["session_id"]
    path = f"/sessions/{sid}/messages"

    def say(text, **extra):
        return ncert_client.post(path, json={"text": text, **extra}).json()

    return sid, say, contexts


def test_follow_up_sees_recent_turns_and_earlier_topics(ncert_client, monkeypatch):
    sid, say, contexts = _lesson(ncert_client, monkeypatch)
    say("Help me understand Acids.", new_topic=True, topic_heading="Acids")
    say("Help me understand Salts.", new_topic=True, topic_heading="Salts")
    say("Explain that.")
    context = contexts[-1]
    assert "Recent chat, oldest first:" in context
    assert "Student: Help me understand Salts." in context and "Tutor: Reply 2:" in context
    assert "Student: Explain that." not in context                # the current message is sent on its own
    assert "Topics covered earlier this session: “Acids”." in context


def test_summary_counts_answers_and_wrong_ones_in_a_row(ncert_client, monkeypatch):
    sid, say, contexts = _lesson(ncert_client, monkeypatch)
    say("Help me understand Salts.", new_topic=True, topic_heading="Salts")
    concept = ncert.concept_id(_passage("Salts"))
    with SessionLocal() as db:
        for correct in (True, True, False):   # one wrong: two would trigger a step back
            learner_model.record(db, "memory-test", ncert.COURSE_ID, sid, concept, correct)
        db.commit()
    say("Explain that.")
    assert "Their last 1 answer on this topic was not right." in contexts[-1]
    assert "On this chapter so far: 2 of 3 answers right." in contexts[-1]
    assert "Skill in Class 10 science:" in contexts[-1]


def test_memory_off_sends_only_the_previous_exchange(ncert_client, monkeypatch):
    monkeypatch.setenv("TUTOR_MEMORY", "off")
    sid, say, contexts = _lesson(ncert_client, monkeypatch)
    say("Help me understand Acids.", new_topic=True, topic_heading="Acids")
    say("Help me understand Salts.", new_topic=True, topic_heading="Salts")
    say("Explain that.")
    context = contexts[-1]
    assert "Student: Help me understand Salts.\nTutor: Reply 2:" in context
    assert "Recent chat" not in context and "Learner so far" not in context


def test_a_new_topic_gets_the_summary_but_not_the_old_chat(ncert_client, monkeypatch):
    sid, say, contexts = _lesson(ncert_client, monkeypatch)
    say("Help me understand Acids.", new_topic=True, topic_heading="Acids")
    say("Help me understand Salts.", new_topic=True, topic_heading="Salts")
    assert "Recent chat" not in contexts[-1]
    assert "Topics covered earlier this session: “Acids”." in contexts[-1]


def test_short_term_drops_the_oldest_turns_to_fit(client):
    with SessionLocal() as db:
        db.add(SessionRow(id="m1", learner_id="l", course_id="demo-math", stack=[], tries=0, pending=None))
        for n in range(8):
            db.add(TurnRow(session_id="m1", role="learner", text=f"question {n} " + "x" * 300))
            db.add(TurnRow(session_id="m1", role="tutor", text="y" * 600 + f" tutor {n}?"))
        db.commit()
        recent, kept = memory.short_term(db, "m1")
    assert len(recent) <= memory.SHORT_TERM_CHARS and 0 < kept < memory.SHORT_TERM_TURNS
    assert recent.endswith("tutor 7?")                             # a tutor turn keeps its end, where its question is
    assert all(len(line) <= len("Student: ") + memory.TUTOR_CHARS for line in recent.splitlines())


def test_visited_keeps_first_seen_order_and_moves_a_revisit_last():
    assert memory.visited(["Acids", "Bases"], "Salts") == ["Acids", "Bases", "Salts"]
    assert memory.visited(["Acids", "Bases"], "Acids") == ["Bases", "Acids"]
    assert memory.visited([], "Salts") == ["Salts"]


# ---- TUTOR_MEMORY=full: notes the model proposes and code checks ----

class _FakeCapture:
    """Stands in for the model: answers only the memory capture prompt, with fixed items."""
    def __init__(self, items):
        self.items, self.calls = items, 0

    def generate(self, prompt, system, max_tokens):
        if system != memory.CAPTURE_SYSTEM:
            raise RuntimeError("only the capture prompt is faked")   # other classifiers then fall back
        self.calls += 1
        return "Here you go:\n" + json.dumps(self.items)


def _full(monkeypatch, items, verdicts):
    monkeypatch.setenv("TUTOR_MEMORY", "full")
    monkeypatch.setenv("MESSAGE_CLASSIFIER_PROVIDER", "fake")
    model = _FakeCapture(items)
    monkeypatch.setattr(llm, "get_provider", lambda provider: model)
    monkeypatch.setattr(socratic, "judge_attempt",
                        lambda student, tutor, problem="": next((v for k, v in verdicts.items() if k in student), None))
    return model


ITEMS = [
    {"kind": "misconception", "turn": 3, "quote": "salts are always neutral", "note": "Thinks all salts are neutral."},
    {"kind": "example_used", "turn": 2, "quote": "what an acid and a base make", "note": "Asked what an acid and a base make."},
    {"kind": "explained", "turn": 4, "quote": "salts dissolve in petrol", "note": "Salts dissolve in petrol."},
    {"kind": "example_used", "turn": 3, "quote": "salts are always neutral", "note": "Neutral salts."},
]


def test_full_memory_keeps_only_checked_notes_and_uses_them(ncert_client, monkeypatch):
    model = _full(monkeypatch, ITEMS, {"always neutral": False})
    sid, say, contexts = _lesson(ncert_client, monkeypatch)
    say("Help me understand Salts.", new_topic=True, topic_heading="Salts")
    say("I think salts are always neutral")
    assert model.calls == 0                                   # not due yet: every third learner turn
    say("Explain that.")
    assert model.calls == 1
    with SessionLocal() as db:
        stored = {(r.kind, r.quote): r.rejected for r in db.scalars(select(MemoryItemRow)).all()}
    assert stored == {("misconception", "salts are always neutral"): None,
                      ("example_used", "what an acid and a base make"): None,
                      ("explained", "salts dissolve in petrol"): "quote not in the chat",
                      ("example_used", "salts are always neutral"): "quote from the wrong speaker"}
    say("Can I have a hint?")
    context = contexts[-1]
    assert "Notes from earlier chat (checked against it):" in context
    assert "- Misconception: Thinks all salts are neutral." in context
    assert "- Example already used: Asked what an acid and a base make." in context
    assert "petrol" not in context and "Neutral salts." not in context


def test_a_right_answer_on_the_topic_retires_its_misconception(ncert_client, monkeypatch):
    _full(monkeypatch, ITEMS[:1], {"always neutral": False, "salt and water": True})
    sid, say, contexts = _lesson(ncert_client, monkeypatch)
    say("Help me understand Salts.", new_topic=True, topic_heading="Salts")
    say("I think salts are always neutral")
    say("Explain that.")
    say("Can I have a hint?")
    assert "Misconception" in contexts[-1]
    say("an acid and a base make a salt and water")               # judged right after this reply
    say("what do you mean?")
    assert "Misconception" not in contexts[-1]


def test_a_misconception_needs_a_wrong_verdict(ncert_client, monkeypatch):
    _full(monkeypatch, ITEMS[:1], {})                             # the judge marked nothing wrong
    sid, say, contexts = _lesson(ncert_client, monkeypatch)
    say("Help me understand Salts.", new_topic=True, topic_heading="Salts")
    say("I think salts are always neutral")
    say("Explain that.")
    with SessionLocal() as db:
        assert [r.rejected for r in db.scalars(select(MemoryItemRow)).all()] == ["answer not judged wrong"]


def test_facts_setting_never_asks_the_model_for_notes(ncert_client, monkeypatch):
    model = _full(monkeypatch, ITEMS, {})
    monkeypatch.setenv("TUTOR_MEMORY", "facts")
    sid, say, contexts = _lesson(ncert_client, monkeypatch)
    for text in ("Help me understand Salts.", "I think salts are always neutral", "Explain that.", "Can I have a hint?"):
        say(text, **({"new_topic": True, "topic_heading": "Salts"} if text.startswith("Help") else {}))
    assert model.calls == 0 and "Notes from earlier chat" not in contexts[-1]


def test_check_rejects_invented_numbers_unknown_kinds_and_bad_replies(client, monkeypatch):
    turns = [(1, "learner", "Is 24 divided by 6 equal to 5?"), (2, "tutor", "Share 24 into 6 equal groups.")]
    with SessionLocal() as db:
        def reason(item):
            return memory._check(db, item, turns, "What is 24 ÷ 6?")[1]
        assert reason({"kind": "open_question", "turn": 1, "quote": "24 divided by 6", "note": "Asked if 24/6 is 4."}) \
            == "number in the note not in the quote"
        assert reason({"kind": "explained", "turn": 2, "quote": "Share 24 into 6 equal groups", "note": "The answer is 4."}) \
            == "number in the note not in the quote"
        assert reason({"kind": "summary", "turn": 1, "quote": "24 divided by 6", "note": "x"}) == "unknown kind"
        assert reason({"kind": "explained", "turn": 9, "quote": "Share 24 into 6", "note": "Sharing into groups."}) is None
        assert reason("not a dict") == "not an item"
    monkeypatch.setenv("MESSAGE_CLASSIFIER_PROVIDER", "fake")
    monkeypatch.setattr(llm, "get_provider", lambda provider: type("M", (), {"generate": lambda *a: "no list here"})())
    assert memory._propose("Salts", turns) is None
