import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)  # clean database per test; startup recreates it and seeds the sample pack
    with TestClient(app) as c:
        yield c


def start(client, learner="l1"):
    r = client.post("/sessions", json={"learner_id": learner, "course_id": "ncert-maths"})
    assert r.status_code == 201
    return r.json()["session_id"]


def say(client, sid, text):
    r = client.post(f"/sessions/{sid}/messages", json={"text": text})
    assert r.status_code == 200
    return r.json()


def test_health_and_courses(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/courses").json()[0]["id"] == "ncert-maths"
    assert len(client.get("/courses/ncert-maths/graph").json()["edges"]) == 3


def test_unknown_course_and_session(client):
    assert client.post("/sessions", json={"learner_id": "x", "course_id": "nope"}).status_code == 404
    assert client.post("/sessions/none/messages", json={"text": "hi"}).status_code == 404


def test_backtracking_loop_reaches_answer_without_revealing_it(client):
    sid = start(client)
    r = say(client, sid, "I am stuck on percentages")
    assert r["action"] == "ask" and r["concept_id"] == "percentages"
    r = say(client, sid, "2.5")                    # wrong -> weak prerequisite
    assert r["action"] == "backtrack" and r["concept_id"] == "fractions"
    r = say(client, sid, "3")                      # wrong again -> deeper
    assert r["action"] == "backtrack" and r["concept_id"] == "division"
    r = say(client, sid, "5")                      # division right -> climb back up
    assert r["action"] == "advance" and r["concept_id"] == "fractions"
    r = say(client, sid, "10")
    assert r["action"] == "advance" and r["concept_id"] == "percentages"
    r = say(client, sid, "10")
    assert r["action"] == "done"
    prog = client.get("/learners/l1/progress", params={"course_id": "ncert-maths"}).json()
    pct = next(c for c in prog["concepts"] if c["concept_id"] == "percentages")
    assert pct["attempts"] == 2 and pct["correct"] == 1


def test_off_topic_and_answer_request_do_not_touch_learner_model(client):
    sid = start(client)
    assert say(client, sid, "who won the cricket match yesterday")["action"] == "redirect"
    say(client, sid, "help with percentages")
    r = say(client, sid, "just tell me the answer")
    assert r["action"] == "redirect" and "10" not in r["reply"]
    prog = client.get("/learners/l1/progress", params={"course_id": "ncert-maths"}).json()
    assert all(c["attempts"] == 0 for c in prog["concepts"])


def test_history_is_separate_per_learner(client):
    a, b = start(client, "a"), start(client, "b")
    say(client, a, "percentages please")
    say(client, a, "wrong")
    pa = client.get("/learners/a/progress", params={"course_id": "ncert-maths"}).json()
    pb = client.get("/learners/b/progress", params={"course_id": "ncert-maths"}).json()
    assert sum(c["attempts"] for c in pa["concepts"]) == 1
    assert sum(c["attempts"] for c in pb["concepts"]) == 0


def test_search_practice_diagnostics_hide_answers(client):
    hits = client.get("/search", params={"course_id": "ncert-maths", "q": "fractions"}).json()
    assert hits and hits[0]["concept_id"] == "fractions"
    qs = client.post("/practice", json={"course_id": "ncert-maths", "concept_id": "division"}).json()
    assert qs and "answer" not in qs[0]
    diag = client.post("/diagnostics", json={"learner_id": "l1", "course_id": "ncert-maths"}).json()
    assert [q["concept_id"] for q in diag][0] == "multiplication"


def test_ingest_rejects_unknown_prerequisite(client):
    pack = {"id": "bad", "title": "Bad", "subject": "x",
            "concepts": [{"id": "a", "name": "A", "level": 1, "prerequisites": ["zzz"]}]}
    assert client.post("/courses", json=pack).status_code == 422
