"""Backtracking triggered by the learner's answers, the weakest prerequisite first, and learner state kept across
sessions as well as per session."""
import pytest

from app.db import SessionLocal
from app.services import learner_model, ncert, socratic

CHAPTER = {"grade": 8, "subject": "maths", "book_code": "hemh1", "chapter": 2}
FRACTIONS_CH = {"grade": 7, "subject": "maths", "book_code": "gemh1", "chapter": 2}
INTEGERS_CH = {"grade": 7, "subject": "maths", "book_code": "gemh1", "chapter": 1}


def _passage(heading, chapter, pid):
    return {**chapter, "passage_id": pid, "heading": heading, "physical_page": 5,
            "source_url": "https://ncert.nic.in/textbook/pdf/x.pdf",
            "content": f"{heading} is explained here in enough detail for a lesson."}


MAIN = _passage("2.3 Percentages", CHAPTER, "main")
INTEGERS = _passage("1.2 Integers", INTEGERS_CH, "integers")
FRACTIONS = _passage("2.1 Fractions", FRACTIONS_CH, "fractions")
PASSAGES = {p["passage_id"]: p for p in (MAIN, INTEGERS, FRACTIONS)}


@pytest.fixture()
def verdicts(monkeypatch):
    """The answer judge says what the test puts in the list, in order (None: no attempt to judge)."""
    queue: list[bool | None] = []
    monkeypatch.setattr(socratic, "judge_attempt", lambda student, reply, problem="": queue.pop(0) if queue else None)
    return queue


@pytest.fixture()
def lesson(ncert_client, monkeypatch, verdicts):
    monkeypatch.setattr(ncert, "topic_passage", lambda scope, heading: MAIN)
    monkeypatch.setattr(ncert, "cited_passage", lambda chapter, pid: PASSAGES[pid])
    monkeypatch.setattr(ncert, "rank", lambda *a, **k: pytest.fail("a follow-up must reuse its source"))
    monkeypatch.setattr(ncert, "prerequisites",
                        lambda row, limit=2: [INTEGERS, FRACTIONS] if row["passage_id"] == "main" else [])
    monkeypatch.setattr(socratic, "_hosted", lambda *args: None)
    path = _open(ncert_client)
    return ncert_client, path


def _open(client):
    sid = client.post("/sessions", json={"course_id": "ncert", "grade": 8, "subject": "maths",
                                         "chapter": CHAPTER}).json()["session_id"]
    path = f"/sessions/{sid}/messages"
    first = client.post(path, json={"text": "Help me understand 2.3 Percentages.", "new_topic": True,
                                    "topic_heading": "2.3 Percentages"}).json()
    assert first["action"] == "explain"
    return path


def _knows(client, chapter, times=3):
    """Record right answers on a chapter for the signed-in learner, in a session of its own (all sessions count)."""
    sid = client.post("/sessions", json={"course_id": "ncert", "grade": 7, "subject": "maths"}).json()["session_id"]
    with SessionLocal() as db:
        for _ in range(times):
            learner_model.record(db, "admin", "ncert", sid, ncert.concept_id(chapter), True)
        db.commit()


def test_two_wrong_answers_step_back_to_the_weakest_prerequisite(lesson, verdicts):
    client, path = lesson
    _knows(client, INTEGERS_CH)                   # strong on integers from an earlier session
    verdicts += [False, False]
    assert client.post(path, json={"text": "x = 5"}).json()["action"] != "backtrack"
    assert client.post(path, json={"text": "x = 7"}).json()["action"] != "backtrack"
    back = client.post(path, json={"text": "x = 9"}).json()
    assert back["action"] == "backtrack"
    assert "Fractions" in back["reply"] and "Integers" not in back["reply"]   # weakest, not the first graph edge
    assert "answers on this topic weren't right" in back["reply"]


def test_a_worded_answer_to_the_tutors_question_is_reviewed_not_searched(lesson):
    # Qwen labels this reply an answer (tests/fake_classifier.py), even though none of its words are in the topic
    # heading: it is reviewed on the open topic, and the lesson fixture fails the test if it is searched again.
    client, path = lesson
    reply = client.post(path, json={"text": "Sodium (Na) and Chloride (Cl)"}).json()
    assert reply["action"] == "hint" and "Are you asking about" not in reply["reply"]


def test_a_right_answer_ends_the_run(lesson, verdicts):
    client, path = lesson
    verdicts += [False, True, False]
    for text in ("x = 5", "x = 6", "x = 7", "x = 8"):
        assert client.post(path, json={"text": text}).json()["action"] != "backtrack"


def test_no_step_back_when_every_prerequisite_is_known(lesson, verdicts):
    client, path = lesson
    _knows(client, INTEGERS_CH)
    _knows(client, FRACTIONS_CH)
    verdicts += [False, False, False, False]
    for text in ("x = 5", "x = 7", "x = 9", "x = 11"):
        assert client.post(path, json={"text": text}).json()["action"] != "backtrack"


def test_returning_to_the_topic_starts_a_fresh_count(lesson, verdicts):
    client, path = lesson
    verdicts += [False, False]
    client.post(path, json={"text": "x = 5"})
    client.post(path, json={"text": "x = 7"})
    assert client.post(path, json={"text": "x = 9"}).json()["action"] == "backtrack"
    back = client.post(path, json={"text": "back to the main topic"}).json()
    assert back["action"] == "advance" and "Percentages" in back["reply"]
    assert client.post(path, json={"text": "x = 12"}).json()["action"] != "backtrack"   # old wrongs don't count


def test_learner_state_is_saved_and_resumed_in_a_new_session(lesson, verdicts, monkeypatch):
    client, path = lesson
    verdicts += [False, False]
    client.post(path, json={"text": "x = 5"})
    client.post(path, json={"text": "x = 7"})
    client.post(path, json={"text": "x = 9"})       # stepped back to an earlier topic

    state = client.get("/learners/admin/state").json()
    assert state["topic"]["heading"] in ("1.2 Integers", "2.1 Fractions")
    assert [e["heading"] for e in state["detour"]] == ["2.3 Percentages"]
    assert client.get("/learners/someone-else/state").status_code == 403

    sid = client.post("/sessions", json={"course_id": "ncert"}).json()["session_id"]
    new = f"/sessions/{sid}/messages"
    assert "Last time you were on" in client.post(new, json={"text": "hi"}).json()["reply"]
    # The path model reads this as "resume", but Qwen's turn label says it names a new subject: no resume,
    # so it is searched for as a new topic (nothing is found here).
    searched = []
    monkeypatch.setattr(ncert, "rank", lambda query, *a, **k: searched.append(query) or [])
    monkeypatch.setattr(socratic, "classify_message", lambda *a, **k: "topic_question")
    other = client.post(new, json={"text": "let's discuss about salts concept"}).json()
    assert "Picking up where you left off" not in other["reply"] and searched
    monkeypatch.setattr(ncert, "rank", lambda *a, **k: pytest.fail("a follow-up must reuse its source"))
    resumed = client.post(new, json={"text": "continue where I left off"}).json()
    assert resumed["action"] == "advance" and "Picking up where you left off" in resumed["reply"]
    assert "Percentages" in resumed["reply"]         # the detour it came from is named, and kept
    main = client.post(new, json={"text": "back to the main topic"}).json()
    assert main["action"] == "advance" and "Percentages" in main["reply"]
    assert client.get("/learners/admin/state").json()["detour"] == []


def test_new_learner_has_an_empty_state(client):
    state = client.get("/learners/admin/state").json()
    assert state["topic"] is None and state["detour"] == []


# ── Answers per graph concept ────────────────────────────────────────────────

def test_judged_answers_are_linked_to_the_topics_graph_concepts(lesson, verdicts, monkeypatch):
    client, path = lesson
    asked = []
    monkeypatch.setattr(ncert, "topic_concepts",
                        lambda topic: asked.append(topic) or ["G-percent", "G-percent-of"])
    verdicts += [True, False]
    client.post(path, json={"text": "x = 5"})
    client.post(path, json={"text": "x = 7"})
    assert asked[0] == {"book_code": "hemh1", "chapter": 2, "heading": "2.3 Percentages"}
    with SessionLocal() as db:
        assert learner_model.stats(db, "admin", "ncert", "G-percent") == (2, 1)
        assert learner_model.stats(db, "admin", "ncert", "G-percent-of") == (2, 1)
        assert learner_model.stats(db, "admin", "ncert", ncert.concept_id(CHAPTER)) == (2, 1)
        assert len(learner_model.history(db, "admin", "ncert")) == 2      # one history entry per answer, not three
        assert learner_model.concept_readiness(db, "admin", "ncert", "G-unseen") is None


def test_step_back_reads_readiness_per_graph_concept(lesson, verdicts, monkeypatch):
    """Two prerequisites in one chapter tie on the chapter; the graph concept answers tell them apart."""
    client, path = lesson
    integers = {**INTEGERS, **FRACTIONS_CH, "concept_id": "G-integers"}
    fractions = {**FRACTIONS, "concept_id": "G-fractions"}
    PASSAGES_SAME = {**PASSAGES, "integers": integers, "fractions": fractions}
    monkeypatch.setattr(ncert, "cited_passage", lambda chapter, pid: PASSAGES_SAME[pid])
    monkeypatch.setattr(ncert, "prerequisites",
                        lambda row, limit=2: [integers, fractions] if row["passage_id"] == "main" else [])
    sid = client.post("/sessions", json={"course_id": "ncert"}).json()["session_id"]
    with SessionLocal() as db:                        # strong on integers, from answers linked to its graph concept
        for _ in range(3):
            learner_model.record(db, "admin", "ncert", sid, "6-maths-fegp1-1", True, ["G-integers"])
        db.commit()
    verdicts += [False, False]
    client.post(path, json={"text": "x = 5"})
    client.post(path, json={"text": "x = 7"})
    back = client.post(path, json={"text": "x = 9"}).json()
    assert back["action"] == "backtrack" and "Fractions" in back["reply"]


# ── Picks from the side panel ────────────────────────────────────────────────

@pytest.fixture()
def by_heading(monkeypatch):
    headings = {p["heading"]: p for p in PASSAGES.values()}
    monkeypatch.setattr(ncert, "topic_passage", lambda scope, heading: headings.get(heading))


def test_a_graph_concept_opens_its_topic_in_another_class(lesson, monkeypatch, by_heading):
    client, path = lesson
    monkeypatch.setattr(ncert, "concept_passage", lambda cid: {**FRACTIONS, "concept": "Fraction"} if cid == "G-fractions" else None)
    reply = client.post(path, json={"text": "Help me understand Fraction.", "new_topic": True,
                                    "graph_concept": "G-fractions"}).json()
    assert reply["action"] == "explain" and reply["chapter"] == FRACTIONS_CH
    assert "Fractions" in client.post(path, json={"text": "where are we?"}).json()["reply"]
    missing = client.post(path, json={"text": "Help me understand Nothing.", "new_topic": True,
                                      "graph_concept": "G-missing"}).json()
    assert "couldn't open that concept" in missing["reply"]


def test_a_pick_with_other_text_is_an_ordinary_message(lesson, monkeypatch):
    client, path = lesson
    monkeypatch.setattr(ncert, "concept_passage", lambda cid: {**FRACTIONS, "concept": "Fraction"})
    reply = client.post(path, json={"text": "where are we?", "graph_concept": "G-fractions"}).json()
    assert "Percentages" in reply["reply"] and "Fractions" not in reply["reply"]


def test_a_topic_in_another_chapter_opens_and_clears_the_detour(lesson, verdicts, by_heading):
    client, path = lesson
    verdicts += [False, False]
    client.post(path, json={"text": "x = 5"})
    client.post(path, json={"text": "x = 7"})
    assert client.post(path, json={"text": "x = 9"}).json()["action"] == "backtrack"
    reply = client.post(path, json={"text": "Help me understand 1.2 Integers.", "new_topic": True,
                                    "topic_heading": "1.2 Integers", "topic_chapter": INTEGERS_CH}).json()
    assert reply["action"] == "explain" and reply["chapter"] == INTEGERS_CH
    assert client.get("/learners/admin/state").json()["detour"] == []


def test_continue_button_resumes_an_earlier_chat(lesson):
    client, path = lesson
    here = client.post(path, json={"text": "Continue where I left off.", "resume": True}).json()
    assert "no saved place" in here["reply"]                 # saved from this chat: nothing to resume
    sid = client.post("/sessions", json={"course_id": "ncert"}).json()["session_id"]
    resumed = client.post(f"/sessions/{sid}/messages", json={"text": "Continue where I left off.", "resume": True}).json()
    assert resumed["action"] == "advance" and "Picking up where you left off" in resumed["reply"]
