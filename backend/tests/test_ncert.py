import io
import json

import pytest
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


@pytest.mark.parametrize("invalid", [None, "revision", "embedding"])
def test_remote_encoder_validates_corpus_compatibility(monkeypatch, invalid):
    query = "What is electric current?"
    vector = [1.0] + [0.0] * 1023
    payload = {"model": ncert.MODEL, "revision": ncert.REVISION, "embedding": vector}
    if invalid == "revision":
        payload["revision"] = "different-revision"
    if invalid == "embedding":
        payload["embedding"] = vector[:-1]

    class EncoderEndpoint:
        def open(self, request, timeout):
            assert request.full_url == "https://encoder.example/embed"
            assert request.get_header("Authorization") == "Bearer test-key"
            assert json.loads(request.data) == {"query": query}
            return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("NCERT_ENABLED", "1")
    monkeypatch.setenv("NCERT_EMBEDDING_URL", "https://encoder.example")
    monkeypatch.setenv("NCERT_EMBEDDING_API_KEY", "test-key")
    monkeypatch.setattr(ncert, "build_opener", lambda *args: EncoderEndpoint())
    if invalid:
        with pytest.raises(HTTPException) as error:
            ncert.rank(query, {})
        assert error.value.status_code == 503
    else:
        assert ncert.embed(query) == vector


def test_production_does_not_load_local_encoder_when_endpoint_is_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("NCERT_ENABLED", "1")
    monkeypatch.delenv("NCERT_EMBEDDING_URL", raising=False)
    monkeypatch.delenv("NCERT_EMBEDDING_API_KEY", raising=False)
    monkeypatch.setattr(ncert, "_encoder", lambda: pytest.fail("Local encoder was called"))

    with pytest.raises(HTTPException) as error:
        ncert.rank("What is electric current?", {})
    assert error.value.status_code == 503


def test_catalogue_selection_scopes_chat_and_search(ncert_client, monkeypatch):
    passage = _passage()
    chapter = {key: passage[key] for key in ("grade", "subject", "book_code", "chapter")}
    monkeypatch.setattr(ncert, "catalogue", lambda grade, subject: [{**chapter, "topics": [passage["heading"]]}])
    monkeypatch.setattr(ncert, "rank", lambda query, scope, **kwargs: [passage] if scope == chapter else [])
    monkeypatch.delenv("NCERT_MODEL_URL", raising=False)

    catalogue = ncert_client.get("/courses/ncert/chapters?grade=10&subject=science").json()
    assert catalogue == [{**chapter, "topics": ["Electric current"]}]
    path = _start(ncert_client, chapter=catalogue[0])
    reply = ncert_client.post(path, json={"text": "Help me understand electric current.", "new_topic": True}).json()
    assert reply["chapter"] == chapter
    hits = ncert_client.get("/search", params={"course_id": "ncert", "q": "current", **chapter}).json()
    assert hits[0]["material"]["url"].endswith("#page=8")


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


def test_topic_switch_respects_selected_subject(ncert_client, monkeypatch):
    fractions = {**_passage(7, "maths"), "chapter": 8, "heading": "Fractions"}
    photosynthesis = {**_passage(7), "chapter": 2, "heading": "Photosynthesis"}

    def rank(query, scope, **kwargs):
        if "photosynthesis" in query:
            return [] if scope.get("subject") == "maths" else [photosynthesis]
        if "fractions" in query:
            return [fractions]
        if query == "What is a cell?":
            return [_passage(7, score=0.80), _passage(10, score=0.79)]
        return []

    monkeypatch.setattr(ncert, "rank", rank)
    for scope in ({}, {"subject": "maths"}):
        path = _start(ncert_client, **scope)
        first = ncert_client.post(path, json={"text": "Teach me fractions"}).json()
        assert first["chapter"]["subject"] == "maths"
        switched = ncert_client.post(path, json={"text": "Can we learn photosynthesis now?"}).json()
        if scope:
            assert switched["label"] == "off_topic"
            hint = ncert_client.post(path, json={"text": "I don't understand why"}).json()
            assert hint["chapter"]["subject"] == "maths"
        else:
            assert switched["chapter"]["subject"] == "science"

    path = _start(ncert_client)
    cell = ncert_client.post(path, json={"text": "What is a cell?"}).json()
    assert cell["action"] == "probe" and cell["resource"] is None
