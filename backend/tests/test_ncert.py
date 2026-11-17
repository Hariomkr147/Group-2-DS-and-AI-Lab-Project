import io
import json

from fastapi import HTTPException

from app.services import ncert, socratic


def _passage(grade=10, subject="science", score=0.8):
    return {
        "grade": grade, "subject": subject, "book_code": "jesc1", "chapter": 11,
        "passage_id": f"{grade}-{subject}-electricity",
        "heading": "Electric current", "physical_page": 8,
        "source_url": "https://ncert.nic.in/textbook/pdf/jesc111.pdf",
        "content": "Electric current is the rate at which electric charge flows through a conductor.",
        "score": score,
    }


def _start(client, **scope):
    response = client.post("/sessions", json={"learner_id": "ncert-test", "course_id": "ncert", **scope})
    assert response.status_code == 201
    return "/sessions/" + response.json()["session_id"] + "/messages"


def test_routes_and_cites_textbook_then_keeps_chapter_for_working(ncert_client, monkeypatch):
    client = ncert_client
    calls = []

    def rank(query, scope, limit=5, *, chapters=False):
        calls.append((query, scope, chapters))
        return [_passage()]

    monkeypatch.setattr(ncert, "rank", rank)
    monkeypatch.delenv("NCERT_MODEL_URL", raising=False)
    path = _start(client, grade=10, subject="science")
    question = "How do I calculate electric current?"
    first = client.post(path, json={"text": question}).json()
    assert calls[0] == (question, {"grade": 10, "subject": "science"}, True)
    assert first["chapter"] == {"grade": 10, "subject": "science", "book_code": "jesc1", "chapter": 11}
    assert first["resource"]["url"].endswith("#page=8")
    assert first["resource"]["passage_id"] == _passage()["passage_id"]
    assert first["generation"] == "extractive"

    followup = client.post(path, json={"text": "2.5"}).json()
    assert calls[1] == (question + "\n2.5", first["chapter"], False)
    assert followup["action"] == "hint"
    assert client.post(path, json={"text": "Just give me the answer"}).json()["label"] == "answer_request"
    assert len(calls) == 2

    results = client.get("/search", params={"course_id": "ncert", "q": question, "grade": 10}).json()
    assert results[0]["passage_id"] == first["resource"]["passage_id"]


def test_ambiguous_route_resumes_original_question_and_outage_is_retryable(ncert_client, monkeypatch):
    client = ncert_client
    path = _start(client)

    def rank(query, scope, limit=5, *, chapters=False):
        if query == "What is electric current?":
            if scope["grade"] is None:
                return [_passage(7, score=0.79), _passage(10, score=0.78)]
            return [_passage(10)]
        raise HTTPException(503, "NCERT is temporarily unavailable.")

    monkeypatch.setattr(ncert, "rank", rank)
    first = client.post(path, json={"text": "What is electric current?"}).json()
    assert first["action"] == "probe" and first["resource"] is None
    response = client.post(path, json={"text": "Class 10 science"}).json()
    assert response["chapter"]["grade"] == 10
    failed = client.post(path, json={"text": "New question", "new_topic": True})
    assert failed.status_code == 503
    session = client.get(path.removesuffix("/messages")).json()
    assert len(session["history"]) == 4


def test_hosted_reply_uses_retrieved_evidence_and_backend_citation(ncert_client, monkeypatch):
    monkeypatch.setenv("NCERT_MODEL_URL", "https://model.example")
    monkeypatch.setenv("NCERT_MODEL_API_KEY", "test-key")
    monkeypatch.setattr(ncert, "rank", lambda *args, **kwargs: [_passage()])

    class ModelEndpoint:
        def open(self, request, timeout):
            assert request.full_url == "https://model.example/predict"
            messages = json.loads(request.data)["messages"]
            evidence = json.loads(messages[1]["content"])["textbook_passage"]
            assert evidence == _passage()["content"]
            return io.BytesIO(json.dumps({
                "task": "socratic_response_generation", "protocol_flags": [],
                "output_limit_reached": False, "text": "What quantity flows per second?",
            }).encode())

    monkeypatch.setattr(socratic, "build_opener", lambda *args: ModelEndpoint())
    reply = ncert_client.post(_start(ncert_client), json={"text": "What is electric current?"}).json()
    assert reply["generation"] == "hosted"
    assert reply["reply"] == "What quantity flows per second?"
    assert reply["resource"]["passage_id"] == _passage()["passage_id"]
