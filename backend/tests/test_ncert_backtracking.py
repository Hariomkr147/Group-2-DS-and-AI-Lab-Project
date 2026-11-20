"""Where-are-we questions, and backtracking through run-time prerequisites in NCERT lessons."""
import pytest

from app.services import conversation, ncert, ncert_path, socratic

CHAPTER = {"grade": 8, "subject": "maths", "book_code": "hemh1", "chapter": 2}
EARLIER = {"grade": 7, "subject": "maths", "book_code": "gemh1", "chapter": 1}


def _passage(heading, chapter, pid, page=5):
    return {**chapter, "passage_id": pid, "heading": heading, "physical_page": page,
            "source_url": "https://ncert.nic.in/textbook/pdf/x.pdf",
            "content": f"{heading} is explained here in enough detail for a lesson."}


MAIN = _passage("2.3 Linear equations", CHAPTER, "main")
BASIC = _passage("1.2 Integers", EARLIER, "basic")


@pytest.mark.parametrize("text", [
    "where are we?", "Which topic are we on?", "what are we studying now?", "what topic are we discussing",
    "which chapter are we in", "what's the current topic", "which topic did we select",
    "tell me the topic we are on", "can you tell me where we are", "what topic am I on"])
def test_where_are_we_phrasings(text):
    assert conversation.asks_where(text)


@pytest.mark.parametrize("text", [
    "what topic should I study now", "explain this topic", "what is a linear equation", "where is 3 + 4",
    "what is this topic about", "hello", "solve 2x = 4"])
def test_other_messages_are_not_where_are_we(text):
    assert not conversation.asks_where(text)


def test_resume_and_prerequisite_phrases():
    assert ncert_path.RESUME.fullmatch("back to the main topic")
    assert ncert_path.RESUME.fullmatch("ok, I get it now")
    assert not ncert_path.RESUME.fullmatch("what is the main topic")
    assert ncert_path.WANTS_BASICS.fullmatch("go back to the basics")
    assert ncert_path.ASKS_PREREQUISITES.fullmatch("what are the prerequisites?")
    assert ncert_path.ASKS_PREREQUISITES.fullmatch("what should I know first")


def _start(client):
    r = client.post("/sessions", json={"learner_id": "t", "course_id": "ncert", "grade": 8, "subject": "maths",
                                       "chapter": CHAPTER})
    assert r.status_code == 201
    return "/sessions/" + r.json()["session_id"] + "/messages"


@pytest.fixture()
def lesson(ncert_client, monkeypatch):
    passages = {"main": MAIN, "basic": BASIC}
    monkeypatch.setattr(ncert, "topic_passage", lambda scope, heading: MAIN)
    monkeypatch.setattr(ncert, "cited_passage", lambda chapter, pid: passages[pid])
    monkeypatch.setattr(ncert, "rank", lambda *a, **k: pytest.fail("a follow-up must reuse its source"))
    monkeypatch.setattr(ncert, "prerequisites", lambda row, limit=2: [BASIC] if row["passage_id"] == "main" else [])
    monkeypatch.setattr(socratic, "_hosted", lambda *args: None)
    path = _start(ncert_client)
    first = ncert_client.post(path, json={"text": "Help me understand 2.3 Linear equations.", "new_topic": True,
                                         "topic_heading": "2.3 Linear equations"}).json()
    assert first["action"] == "explain"
    return ncert_client, path


def test_where_are_we_names_the_selected_topic(lesson):
    client, path = lesson
    for text in ("where are we?", "which chapter are we in", "what is the current topic?"):
        reply = client.post(path, json={"text": text}).json()
        assert "Linear equations" in reply["reply"], text


def test_repeated_confusion_steps_back_then_resumes(lesson):
    client, path = lesson
    assert client.post(path, json={"text": "Can I have a hint?"}).json()["action"] == "hint"
    back = client.post(path, json={"text": "I still don't understand"}).json()
    assert back["action"] == "backtrack" and "Integers" in back["reply"] and back["level"] == 7
    where = client.post(path, json={"text": "where are we?"}).json()["reply"]
    assert "Integers" in where and "Linear equations" in where
    again = client.post(path, json={"text": "back to the main topic"}).json()
    assert again["action"] == "advance" and "Linear equations" in again["reply"] and again["level"] == 8
    assert "Welcome back" in again["reply"]


def test_learner_can_ask_for_prerequisites_and_basics(lesson):
    client, path = lesson
    listed = client.post(path, json={"text": "what are the prerequisites?"}).json()
    assert "Integers" in listed["reply"] and listed["action"] != "backtrack"
    basics = client.post(path, json={"text": "go back to the basics"}).json()
    assert basics["action"] == "backtrack" and "Integers" in basics["reply"]


def test_no_prerequisite_means_no_detour(lesson, monkeypatch):
    client, path = lesson
    monkeypatch.setattr(ncert, "prerequisites", lambda row, limit=2: [])
    client.post(path, json={"text": "Can I have a hint?"})
    reply = client.post(path, json={"text": "I still don't understand"}).json()
    assert reply["action"] != "backtrack"


def test_picking_a_topic_clears_the_detour(lesson):
    client, path = lesson
    client.post(path, json={"text": "Can I have a hint?"})
    client.post(path, json={"text": "I still don't understand"})
    client.post(path, json={"text": "Help me understand 2.3 Linear equations.", "new_topic": True,
                            "topic_heading": "2.3 Linear equations"})
    assert "Integers" not in client.post(path, json={"text": "where are we?"}).json()["reply"]


def test_pack_tutor_says_where_we_are_after_a_backtrack(client):
    sid = client.post("/sessions", json={"learner_id": "w", "course_id": "ncert-maths"}).json()["session_id"]
    path = f"/sessions/{sid}/messages"
    assert "haven't started" in client.post(path, json={"text": "where are we?"}).json()["reply"]
    client.post(path, json={"text": "I am stuck on percentages"})
    client.post(path, json={"text": "2.5"})                     # wrong: steps back to fractions
    reply = client.post(path, json={"text": "which topic are we on?"}).json()["reply"]
    assert "Fractions" in reply and "Percentages" in reply
