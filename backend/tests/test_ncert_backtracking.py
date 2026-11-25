"""Where-are-we questions, and backtracking through run-time prerequisites in NCERT lessons."""
import pytest
from fastapi import HTTPException

from app.schemas import ChapterTopics
from app.services import conversation, ncert, ncert_path, socratic

CHAPTER = {"grade": 8, "subject": "maths", "book_code": "hemh1", "chapter": 2}
EARLIER = {"grade": 7, "subject": "maths", "book_code": "gemh1", "chapter": 1}


def _passage(heading, chapter, pid, page=5):
    return {**chapter, "passage_id": pid, "heading": heading, "physical_page": page,
            "source_url": "https://ncert.nic.in/textbook/pdf/x.pdf",
            "content": f"{heading} is explained here in enough detail for a lesson."}


MAIN = _passage("2.3 Linear equations", CHAPTER, "main")
BASIC = _passage("1.2 Integers", EARLIER, "basic")


class _Model:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def generate(self, prompt, system, max_tokens):
        self.calls.append((prompt, system))
        return self.reply


@pytest.mark.parametrize("reply, label", [
    ("resume", "resume"), (" Understood.", "understood"), ("'basics'", "basics"), ("PREREQUISITES", "prerequisites"),
    ("main_topic", "main_topic"), ("Deepest", "deepest"),
    ("other", None), ("I think they want the basics", None), ("", None),
])
def test_path_classifier_keeps_only_its_labels(monkeypatch, fake_path_classifier, reply, label):
    from app.services import llm
    model = _Model(reply)
    monkeypatch.setenv("MESSAGE_CLASSIFIER_PROVIDER", "fake")
    monkeypatch.setattr(llm, "get_provider", lambda name: model)
    assert fake_path_classifier("back to the main topic", detour=True) == label
    assert '"back to the main topic"' == model.calls[0][0] and "stepped back" in model.calls[0][1]


def test_path_classifier_skips_long_messages_and_survives_a_missing_model(monkeypatch, fake_path_classifier):
    from app.services import llm
    monkeypatch.setenv("MESSAGE_CLASSIFIER_PROVIDER", "fake")
    monkeypatch.setattr(llm, "get_provider", lambda name: pytest.fail("no model call for long messages"))
    assert fake_path_classifier("x" * 121) is None
    monkeypatch.setattr(llm, "get_provider", lambda name: (_ for _ in ()).throw(RuntimeError("down")))
    assert fake_path_classifier("got it") is None
    monkeypatch.setenv("MESSAGE_CLASSIFIER_PROVIDER", "templates")
    assert fake_path_classifier("got it") is None


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
    assert "Welcome to" in again["reply"]


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
    where = client.post(path, json={"text": "where are we?"}).json()["reply"]
    assert "Integers" not in where and "stepped back" not in where
    assert "Welcome to" not in client.post(path, json={"text": "back to the main topic"}).json()["reply"]


def test_pack_tutor_says_where_we_are_after_a_backtrack(client):
    sid = client.post("/sessions", json={"learner_id": "w", "course_id": "ncert-maths"}).json()["session_id"]
    path = f"/sessions/{sid}/messages"
    assert "haven't started" in client.post(path, json={"text": "where are we?"}).json()["reply"]
    client.post(path, json={"text": "I am stuck on percentages"})
    client.post(path, json={"text": "2.5"})                     # wrong: steps back to fractions
    reply = client.post(path, json={"text": "which topic are we on?"}).json()["reply"]
    assert "Fractions" in reply and "Percentages" in reply


def test_graph_prerequisite_names_the_concept_it_comes_from(lesson, monkeypatch):
    client, path = lesson
    graph_row = {**BASIC, "concept": "Integer", "for_concept": "Linear equation", "reason": "", "score": 0.95,
                 "source": "graph"}
    monkeypatch.setattr(ncert, "prerequisites", lambda row, limit=2: [graph_row] if row["passage_id"] == "main" else [])
    listed = client.post(path, json={"text": "what are the prerequisites?"}).json()["reply"]
    assert "Integer, in “Integers”" in listed
    back = client.post(path, json={"text": "go back to the basics"}).json()
    assert back["action"] == "backtrack" and "we meet Integer, which Linear equation needs" in back["reply"]


def test_prerequisites_ask_the_graph_first_then_fall_back(monkeypatch):
    calls = []

    def fake_query(statement, scope, **extra):
        graph = statement is ncert._GRAPH_PREREQUISITES
        calls.append("graph" if graph else "embedding")
        return [dict(BASIC, score=0.9)] if graph == use_graph else []

    monkeypatch.setattr(ncert, "_query", fake_query)
    use_graph = True
    assert [r["source"] for r in ncert.prerequisites(MAIN)] == ["graph"] and calls == ["graph"]
    calls.clear(); use_graph = False
    assert [r["source"] for r in ncert.prerequisites(MAIN)] == ["embedding"] and calls == ["graph", "embedding"]
    calls.clear(); monkeypatch.setenv("NCERT_GRAPH", "0")
    assert [r["source"] for r in ncert.prerequisites(MAIN)] == ["embedding"] and calls == ["embedding"]


def test_missing_graph_tables_fall_back_to_embeddings(monkeypatch):
    def fake_query(statement, scope, **extra):
        if statement is ncert._GRAPH_PREREQUISITES:
            raise ncert.HTTPException(503, "The NCERT evidence database is unavailable.")
        return [dict(BASIC, score=0.9)]

    monkeypatch.setattr(ncert, "_query", fake_query)
    assert [r["source"] for r in ncert.prerequisites(MAIN)] == ["embedding"]


# ── Forward tracking: climbing back out of detours and moving on through the chapter ─────────────────────────────
OLDER = {"grade": 6, "subject": "maths", "book_code": "fegp1", "chapter": 3}
MID = _passage("1.4 Negative numbers", EARLIER, "mid")
ROOT = _passage("3.1 Counting numbers", OLDER, "root")
NEXT = _passage("2.4 Solving equations", CHAPTER, "next")
TOPICS = ["2.1 Introduction", "2.3 Linear equations", "2.4 Solving equations"]


@pytest.fixture()
def chain(ncert_client, monkeypatch):
    """Main (class 8) builds on mid (class 7), which builds on basic, which builds on root (class 6)."""
    passages = {p["passage_id"]: p for p in (MAIN, MID, BASIC, ROOT, NEXT)}
    builds_on = {"main": [MID], "mid": [BASIC], "basic": [ROOT], "root": []}
    by_heading = {p["heading"]: p for p in passages.values()}
    monkeypatch.setattr(ncert, "topic_passage", lambda scope, heading: by_heading.get(heading))
    monkeypatch.setattr(ncert, "cited_passage", lambda chapter, pid: passages[pid])
    monkeypatch.setattr(ncert, "prerequisites", lambda row, limit=2: builds_on.get(row["passage_id"], []))
    monkeypatch.setattr(ncert, "catalogue", lambda grade, subject: [
        ChapterTopics(**CHAPTER, title="Linear Equations", topics=TOPICS)])
    monkeypatch.setattr(ncert, "rank", lambda *a, **k: [])
    monkeypatch.setattr(ncert, "similarity", lambda *a, **k: 0.0)
    monkeypatch.setattr(socratic, "_hosted", lambda *args: None)
    path = _start(ncert_client)
    ncert_client.post(path, json={"text": "Help me understand 2.3 Linear equations.", "new_topic": True,
                                  "topic_heading": "2.3 Linear equations"})
    return ncert_client, path


def _say(client, path, text):
    return client.post(path, json={"text": text}).json()


def test_two_level_detour_climbs_back_one_level_at_a_time(chain):
    client, path = chain
    assert _say(client, path, "go back to the basics")["level"] == 7                     # main -> negative numbers
    deeper = _say(client, path, "go back to the basics")                                 # -> integers
    assert deeper["action"] == "backtrack" and "Integers" in deeper["reply"]

    up = _say(client, path, "back to the previous topic")
    assert up["action"] == "advance" and up["level"] == 7 and "Welcome to “Negative numbers”" in up["reply"]
    top = _say(client, path, "back to the previous topic")
    assert top["action"] == "advance" and top["level"] == 8 and "Welcome to “Linear equations”" in top["reply"]
    assert "Integers" not in _say(client, path, "where are we?")["reply"]                # the stack is empty again


def test_detours_go_as_deep_as_the_prerequisites_and_climb_back_one_level_at_a_time(chain, monkeypatch):
    client, path = chain
    first = _passage("1.1 Numbers around us", OLDER, "first")                          # a fourth level: no depth limit
    passages = {p["passage_id"]: p for p in (MAIN, MID, BASIC, ROOT, NEXT, first)}
    builds_on = {"main": [MID], "mid": [BASIC], "basic": [ROOT], "root": [first], "first": []}
    monkeypatch.setattr(ncert, "cited_passage", lambda chapter, pid: passages[pid])
    monkeypatch.setattr(ncert, "prerequisites", lambda row, limit=2: builds_on[row["passage_id"]])
    for expected in ("Negative numbers", "Integers", "Counting numbers", "Numbers around us"):
        reply = _say(client, path, "go back to the basics")
        assert reply["action"] == "backtrack" and expected in reply["reply"]
    assert _say(client, path, "go back to the basics")["action"] != "backtrack"         # no earlier topic left
    for expected in ("Counting numbers", "Integers", "Negative numbers", "Linear equations"):
        assert f"Welcome to “{expected}”" in _say(client, path, "back to the previous topic")["reply"]


def test_help_counter_starts_again_inside_a_detour(chain):
    client, path = chain
    actions = [_say(client, path, t)["action"] for t in
               ("Can I have a hint?", "I still don't understand",       # lost on main: step back to negative numbers
                "Can I have a hint?", "I still don't understand")]      # lost there too: only now step back again
    assert actions == ["hint", "backtrack", "hint", "backtrack"]
    assert "Integers" in _say(client, path, "where are we?")["reply"]


def test_help_counter_starts_again_after_climbing_back(chain):
    client, path = chain
    _say(client, path, "go back to the basics")
    _say(client, path, "back to the main topic")
    assert _say(client, path, "Can I have a hint?")["action"] == "hint"                  # not an instant detour


def test_understood_moves_to_the_next_topic_in_the_chapter(chain, monkeypatch):
    client, path = chain
    monkeypatch.setattr(socratic, "classify_message", lambda text, topic_open=False: "understood")
    reply = _say(client, path, "cool, what's next")
    assert reply["action"] == "advance" and reply["reply"].startswith("Great! Let's move on.")
    assert reply["resource"]["passage_id"] == "next"
    assert "Solving equations" in _say(client, path, "where are we?")["reply"]


def test_understood_on_the_last_topic_ends_the_chapter(chain, monkeypatch):
    client, path = chain
    monkeypatch.setattr(socratic, "classify_message", lambda text, topic_open=False: "understood")
    _say(client, path, "cool, what's next")                                              # now on 2.4, the last topic
    assert "end of this chapter's topics" in _say(client, path, "cool, what's next")["reply"]


def test_understood_inside_a_detour_climbs_back_instead_of_skipping_ahead(chain, monkeypatch):
    client, path = chain
    _say(client, path, "go back to the basics")
    monkeypatch.setattr(socratic, "classify_message", lambda text, topic_open=False: "understood")
    reply = _say(client, path, "cool, what's next")
    assert reply["action"] == "advance" and reply["level"] == 8 and "Welcome to" in reply["reply"]


def test_resume_when_the_saved_topic_is_gone_asks_for_a_topic(chain, monkeypatch):
    client, path = chain
    _say(client, path, "go back to the basics")
    monkeypatch.setattr(ncert, "cited_passage", lambda chapter, pid: (_ for _ in ()).throw(
        HTTPException(503, "The NCERT evidence database is unavailable.")))
    assert "Pick the topic you were on" in _say(client, path, "back to the main topic")["reply"]


# ── Review fixes ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_got_it_inside_a_detour_resumes_even_when_the_classifier_says_thanks(chain, monkeypatch):
    client, path = chain
    monkeypatch.setattr(conversation, "classify", lambda text, question="": "thanks" if "basics" not in text else None)
    for text in ("got it", "ok, that makes sense"):
        assert _say(client, path, "go back to the basics")["action"] == "backtrack"
        reply = _say(client, path, text)
        assert reply["action"] == "advance" and "Welcome to" in reply["reply"], text


def test_back_to_the_main_topic_without_a_detour_says_we_are_on_it(lesson):
    client, path = lesson
    reply = client.post(path, json={"text": "back to the main topic"}).json()["reply"]
    assert "already on the main topic" in reply and "Linear equations" in reply


def test_got_it_without_a_detour_moves_to_the_next_topic(chain, monkeypatch):
    client, path = chain
    monkeypatch.setattr(conversation, "classify", lambda text, question="": "thanks")
    reply = _say(client, path, "I understand now")
    assert reply["action"] == "advance" and reply["resource"]["passage_id"] == "next"


def test_help_count_does_not_carry_over_to_a_new_topic(chain):
    client, path = chain
    client.post(path, json={"text": "Help me understand 2.4 Solving equations.", "new_topic": True,
                            "topic_heading": "2.4 Solving equations"})
    assert _say(client, path, "Can I have a hint?")["action"] == "hint"
    client.post(path, json={"text": "Help me understand 2.3 Linear equations.", "new_topic": True,
                            "topic_heading": "2.3 Linear equations"})
    assert _say(client, path, "Can I have a hint?")["action"] == "hint"                 # not an instant detour


def test_step_back_uses_the_topic_not_the_chunk_a_follow_up_found(chain, monkeypatch):
    client, path = chain
    monkeypatch.setattr(ncert, "rank", lambda *a, **k: [{**NEXT, "score": 0.9}])        # a chunk under 2.4
    _say(client, path, "In linear equations, why do we move terms across?")
    back = _say(client, path, "go back to the basics")
    assert back["action"] == "backtrack" and "Negative numbers" in back["reply"]       # main's prerequisite
    assert "Welcome to “Linear equations”" in _say(client, path, "back to the main topic")["reply"]


def test_move_on_survives_a_missing_corpus(chain, monkeypatch):
    client, path = chain
    monkeypatch.setattr(ncert, "catalogue", lambda *a: (_ for _ in ()).throw(HTTPException(503, "down")))
    reply = _say(client, path, "got it")
    assert "can't open the next topic" in reply["reply"]


def test_new_ones_skips_other_chunks_of_a_topic_on_the_way():
    other_chunk = {**MAIN, "passage_id": "main-2"}
    stack = [ncert_path.entry(MID, EARLIER)]
    assert ncert_path.new_ones([other_chunk, {**MID, "passage_id": "mid-2"}, BASIC], MAIN, stack) == [BASIC]
    intro_elsewhere = _passage("2.1 Introduction", EARLIER, "intro")
    assert ncert_path.new_ones([intro_elsewhere], _passage("2.1 Introduction", CHAPTER, "here"), []) == [intro_elsewhere]


def test_graph_prerequisites_are_limited_to_earlier_topics(monkeypatch):
    seen = {}

    def fake_query(statement, scope, **extra):
        seen.update(extra)
        return []

    monkeypatch.setattr(ncert, "_query", fake_query)
    ncert.graph_prerequisites(MAIN)
    assert seen["cur_page"] == MAIN["physical_page"]
    assert "p.chapter, p.physical_page" in str(ncert._GRAPH_PREREQUISITES)


# ── Multi-step jumps ─────────────────────────────────────────────────────────────────────────────────────────────
def test_back_to_the_main_topic_jumps_over_every_level(chain):
    client, path = chain
    _say(client, path, "go back to the basics")
    deeper = _say(client, path, "go back to the basics")
    assert deeper["action"] == "backtrack" and "back to the" not in deeper["reply"]     # no return wording in the reply
    where = _say(client, path, "where are we?")["reply"]
    assert "The main topic is “Linear equations”" in where and "back to the previous topic" in where
    top = _say(client, path, "back to the main topic")
    assert top["action"] == "advance" and top["level"] == 8 and "Welcome to “Linear equations”" in top["reply"]
    assert "stepped back" not in _say(client, path, "where are we?")["reply"]           # the stack is empty
    assert "already on the main topic" in _say(client, path, "back to the main topic")["reply"]


def test_start_from_the_very_basics_jumps_to_the_deepest_prerequisite(chain):
    client, path = chain
    deep = _say(client, path, "start from the very basics")
    assert deep["action"] == "backtrack" and deep["level"] == 6 and "Counting numbers" in deep["reply"]
    assert "pass through “Integers”, “Negative numbers”" in deep["reply"]
    for expected in ("Integers", "Negative numbers", "Linear equations"):                # foundations first, back up
        assert f"Welcome to “{expected}”" in _say(client, path, "back to the previous topic")["reply"]


def test_deepest_from_inside_a_detour_keeps_the_way_back(chain):
    client, path = chain
    _say(client, path, "go back to the basics")                                          # main -> mid
    assert "Counting numbers" in _say(client, path, "start from the very basics")["reply"]
    assert "Welcome to “Linear equations”" in _say(client, path, "back to the main topic")["reply"]


def test_deepest_with_no_prerequisite_lists_none(lesson, monkeypatch):
    client, path = lesson
    monkeypatch.setattr(ncert, "prerequisites", lambda row, limit=2: [])
    reply = client.post(path, json={"text": "start from the very basics"}).json()
    assert reply["action"] != "backtrack" and "couldn't find an earlier topic" in reply["reply"]
