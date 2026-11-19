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


def test_hosted_hint_leaves_the_student_a_question(monkeypatch):
    monkeypatch.setattr(socratic, "_hosted", lambda *args: "Think about charge flowing through a wire.")
    reply, mode = socratic.grounded("Explain that.", "Electric current", _passage())
    assert mode == "hosted" and reply.startswith("Think about charge") and reply.endswith("?")
    followup, mode = socratic.grounded("What do you mean?", "Electric current", _passage(), previous_reply=reply)
    assert mode == "extractive" and followup != reply


def test_point_lesson_explains_and_hints_without_searching_again(ncert_client, monkeypatch):
    chapter = {"grade": 6, "subject": "maths", "book_code": "fegp1", "chapter": 2}
    definition = "A point marks a precise location and has no length, breadth or height."
    example = "A dot made with a sharp pencil gives you an idea of a point."
    passage = {**_passage(6, "maths"), **chapter, "heading": "2.1 Point",
               "content": f"{example} {definition}"}
    monkeypatch.setattr(ncert, "topic_passage", lambda *args: passage)
    monkeypatch.setattr(ncert, "cited_passage", lambda *args: passage)
    monkeypatch.setattr(ncert, "rank", lambda *args, **kwargs: pytest.fail("Follow-up should reuse its source"))
    modes = []

    def hosted(text, context, evidence, mode):
        modes.append(mode)
        if mode == "hint":
            return "Look at the textbook and try the exercise again."
        return "What is a point in geometry?"

    monkeypatch.setattr(socratic, "_hosted", hosted)
    path = _start(ncert_client, chapter=chapter)
    first = ncert_client.post(path, json={"text": "Help me understand 2.1 Point.", "new_topic": True,
                                         "topic_heading": "2.1 Point"}).json()
    assert first["action"] == "explain" and definition in first["reply"]
    hint = ncert_client.post(path, json={"text": "Can I have a hint?"}).json()
    assert hint["action"] == "hint" and hint["resource"] == first["resource"]
    assert "Look at the textbook" not in hint["reply"]
    again = ncert_client.post(path, json={"text": "i am not referring to textbook"}).json()
    assert again["action"] == "explain" and definition in again["reply"]
    assert modes == ["explain", "hint", "explain"]


def test_problem_context_guides_work_and_blocks_known_result(ncert_client, monkeypatch):
    passage = {**_passage(6, "maths"), "heading": "Division",
               "content": "Division shares items into equal groups. For example, 24 divided by 6 is 4."}
    monkeypatch.setattr(ncert, "rank", lambda *args, **kwargs: [passage])
    monkeypatch.setattr(ncert, "cited_passage", lambda *args: passage)
    contexts = []

    def hosted(text, context, evidence, mode):
        contexts.append((context, mode))
        if mode == "guide":
            return "Think about sharing into equal groups. How many items go in each group?"
        return "There are 4 items in each group. How can you check?"

    monkeypatch.setattr(socratic, "_hosted", hosted)
    path = _start(ncert_client, grade=6, subject="maths")
    first = ncert_client.post(path, json={"text": "What is 24 ÷ 6?"}).json()
    assert first["action"] == "guide" and first["generation"] == "hosted"
    hint = ncert_client.post(path, json={"text": "Can I have a hint?"}).json()
    assert hint["action"] == "hint" and hint["generation"] == "extractive"
    assert "Use multiplication" in hint["reply"] and "4 items" not in hint["reply"]
    assert "Current exercise: What is 24 ÷ 6?" in contexts[-1][0]
    wrong = ncert_client.post(path, json={"text": "24 / 6 = 5"}).json()
    assert wrong["wrong_step"] == 1 and "Recheck the arithmetic" in wrong["reply"]
    assert ncert_client.post(path, json={"text": "Just give me the answer"}).json()["label"] == "answer_request"


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
    monkeypatch.setattr(ncert, "_query", lambda *args, **kwargs: [{**chapter, "topics": [passage["heading"]]}])
    monkeypatch.setattr(ncert, "rank", lambda query, scope, **kwargs: [passage] if scope == chapter else [])
    monkeypatch.delenv("NCERT_MODEL_URL", raising=False)

    catalogue = ncert_client.get("/courses/ncert/chapters?grade=10&subject=science").json()
    assert catalogue == [{**chapter, "title": "Electricity", "topics": ["Electric current"]}]
    path = _start(ncert_client, chapter=catalogue[0])
    reply = ncert_client.post(path, json={"text": "Help me understand electric current.", "new_topic": True}).json()
    assert reply["chapter"] == chapter
    hits = ncert_client.get("/search", params={"course_id": "ncert", "q": "current", **chapter}).json()
    assert hits[0]["material"]["url"].endswith("#page=8")


def test_chapter_buttons_open_exact_sections_and_keep_context_for_a_typo(ncert_client, monkeypatch):
    chapter = {"grade": 10, "subject": "maths", "book_code": "jemh1", "chapter": 1}
    intro = {**_passage(), **chapter, "heading": "1.1 Introduction", "physical_page": 1,
             "passage_id": "intro", "source_url": "https://ncert.nic.in/textbook/pdf/jemh101.pdf"}
    theorem = {**intro, "heading": "1.2 The Fundamental Theorem of Arithmetic", "physical_page": 2,
               "passage_id": "theorem", "content": "Every composite number can be expressed as a product of primes."}
    topics = {row["heading"]: row for row in (intro, theorem)}
    calls = []

    def topic_passage(scope, heading):
        assert scope == chapter
        return topics.get(heading)

    def rank(query, scope, **kwargs):
        calls.append((query, scope, kwargs))
        return [theorem]

    monkeypatch.setattr(ncert, "topic_passage", topic_passage)
    monkeypatch.setattr(ncert, "rank", rank)
    monkeypatch.setattr(socratic.guardrails, "classify_input", lambda *args: ("uncertain", "uncertain"))
    monkeypatch.setattr(socratic, "_hosted", lambda *args: "What is the Fundamental Theorem of Arithmetic?")
    path = _start(ncert_client, chapter=chapter)

    def pick(heading):
        return ncert_client.post(path, json={"text": f"Help me understand {heading}.", "new_topic": True,
                                             "topic_heading": heading}).json()

    assert pick(intro["heading"])["resource"]["passage_id"] == "intro"
    result = pick(theorem["heading"])
    assert result["resource"]["url"].endswith("#page=2")
    assert result["generation"] == "extractive"
    assert theorem["content"] in result["reply"]
    assert pick("A NOTE TO THE READER")["resource"] is None
    assert calls == []

    followup = ncert_client.post(path, json={"text": "what is arithmatic ?"}).json()
    assert followup["action"] == "explain"
    assert followup["reply"] != result["reply"]
    assert followup["resource"]["passage_id"] == "theorem"
    assert calls == [("The Fundamental Theorem of Arithmetic\nwhat is arithmatic ?", chapter, {"limit": 1})]


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

    contexts = []
    def cited(chapter, passage_id):
        assert chapter == first["chapter"] and passage_id == first["resource"]["passage_id"]
        return _passage()

    monkeypatch.setattr(ncert, "cited_passage", cited)
    monkeypatch.setattr(socratic, "_hosted", lambda text, context, evidence, mode: contexts.append(context))
    followup = client.post(path, json={"text": "2.5"}).json()
    assert first["reply"] in contexts[-1]
    assert followup["action"] == "hint"
    assert client.post(path, json={"text": "what do you mean?"}).json()["resource"] == first["resource"]
    assert "Student: 2.5" in contexts[-1]
    assert client.post(path, json={"text": "Just give me the answer"}).json()["label"] == "answer_request"
    assert len(calls) == 1

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


@pytest.mark.parametrize("url, outcome", [
    ("https://model.example", "hosted"),
    ("https://model-demo.hf.space", "hosted"),
    ("https://model-demo.hf.space", "extractive"),
])
def test_hosted_reply_uses_retrieved_evidence_and_backend_citation(ncert_client, monkeypatch, url, outcome):
    monkeypatch.setenv("NCERT_MODEL_URL", url)
    monkeypatch.setenv("NCERT_MODEL_API_KEY", "test-key")
    monkeypatch.setattr(ncert, "rank", lambda *args, **kwargs: [_passage()])

    class ModelEndpoint:
        def open(self, request, timeout):
            assert request.get_header("Authorization") == "Bearer test-key"
            result = {
                "task": "socratic_response_generation", "protocol_flags": [],
                "output_limit_reached": outcome == "extractive",
                "text": "Current measures how much charge passes per second. What quantity is flowing?",
            }
            if url.endswith(".hf.space"):
                endpoint = f"{url}/gradio_api/call/predict_grounded"
                if request.data is None:
                    assert request.full_url == f"{endpoint}/test-event"
                    return io.BytesIO(f"event: complete\ndata: {json.dumps([result])}\n\n".encode())
                assert request.full_url == endpoint
                system, text = json.loads(request.data)["data"]
                assert "Use the textbook passage only as evidence" in system
                response = {"event_id": "test-event"}
            else:
                assert request.full_url == f"{url}/predict"
                messages = json.loads(request.data)["messages"]
                text = messages[1]["content"]
                response = result
            assert json.loads(text)["textbook_passage"] == _passage()["content"]
            return io.BytesIO(json.dumps(response).encode())

    monkeypatch.setattr(socratic, "build_opener", lambda *args: ModelEndpoint())
    reply = ncert_client.post(_start(ncert_client), json={"text": "What is electric current?"}).json()
    assert reply["generation"] == outcome
    if outcome == "hosted":
        assert reply["reply"].startswith("Current measures how much charge")
    else:
        assert _passage()["content"] in reply["reply"]
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
    monkeypatch.setattr(ncert, "cited_passage", lambda chapter, passage_id: fractions)
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
