"""GET /learners/{id}/graph: the learning graph with one learner's mastery on each concept."""
from app.db import SessionLocal
from app.services import learner_model

from .test_ncert_graph import _fake


def _answers(client, results: dict[str, list[bool]], learner="admin"):
    """Record answers linked to graph concepts (as the judge does), in one session of the learner."""
    sid = client.post("/sessions", json={"course_id": "ncert", "learner_id": learner}).json()["session_id"]
    with SessionLocal() as db:
        for concept, oks in results.items():
            for ok in oks:
                learner_model.record(db, learner, "ncert", sid, "8-maths-b8-2", ok, [concept])
        db.commit()


def _graph(client, **params):
    r = client.get("/learners/admin/graph", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_statuses_and_next_concepts(ncert_client, monkeypatch):
    _fake(monkeypatch)
    _answers(ncert_client, {"int": [True] * 3, "var": [True] * 3, "area": [False, False]})
    graph = _graph(ncert_client)
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert nodes["int"]["status"] == "mastered" and nodes["int"]["readiness"] == 0.8
    assert (nodes["int"]["attempts"], nodes["int"]["correct"], nodes["int"]["source"]) == (3, 3, "accuracy")
    assert nodes["area"]["status"] == "struggling" and nodes["area"]["readiness"] == 0.25
    assert nodes["lin"]["status"] == "ready"                 # both prerequisites mastered, not tried yet
    assert nodes["lin"]["readiness"] is None and nodes["lin"]["prerequisites"] == ["int", "var"]
    assert graph["next"] == ["lin"] and graph["review"] == ["area"]
    assert graph["counts"] == {"mastered": 2, "learning": 0, "struggling": 1, "ready": 1, "unseen": 0}
    assert {(e["prerequisite"], e["concept"]) for e in graph["edges"]} == {("int", "lin"), ("var", "lin")}


def test_a_prerequisite_still_being_learned_keeps_the_concept_unseen(ncert_client, monkeypatch):
    _fake(monkeypatch)
    _answers(ncert_client, {"int": [True] * 3, "var": [True, True, False]})   # (2 + 1) / (3 + 2) = 0.6
    nodes = {n["id"]: n for n in _graph(ncert_client)["nodes"]}
    assert nodes["var"]["status"] == "learning" and nodes["lin"]["status"] == "unseen"
    assert nodes["area"]["status"] == "unseen"               # no prerequisites: never ready by default


def test_new_learner_sees_everything_unseen(ncert_client, monkeypatch):
    _fake(monkeypatch)
    graph = _graph(ncert_client)
    assert {n["status"] for n in graph["nodes"]} == {"unseen"} and graph["next"] == [] and graph["review"] == []


def test_other_learners_answers_do_not_count(ncert_client, monkeypatch):
    _fake(monkeypatch)
    _answers(ncert_client, {"int": [True] * 3}, learner="someone-else")
    assert {n["status"] for n in _graph(ncert_client)["nodes"]} == {"unseen"}


def test_scoped_graph_and_access(ncert_client, monkeypatch):
    _fake(monkeypatch)
    graph = _graph(ncert_client, grade=8, subject="maths", chapter=2)
    assert {n["id"] for n in graph["nodes"]} == {"int", "var", "lin"}
    assert ncert_client.get("/learners/someone-else/graph").status_code == 403
    assert ncert_client.get("/learners/admin/graph", params={"grade": 12}).status_code == 422
