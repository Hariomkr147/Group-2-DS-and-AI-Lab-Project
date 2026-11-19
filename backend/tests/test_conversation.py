import pytest

from app.services import conversation

from .test_api import say, start


@pytest.mark.parametrize("text, kind", [
    ("hello", "greeting"), ("Hi there!", "greeting"), ("can you say hello to me?", "greeting"),
    ("thanks", "thanks"), ("ok thanks", "thanks"), ("bye", "bye"),
    ("yes please", "yes"), ("ok", "yes"), ("next", "practice"), ("quiz me", "practice"),
    ("give me a harder one", "harder"), ("an easier question", "easier"), ("I don't know", "idk"),
    ("what can you do?", "menu"), ("which topics can I learn?", "menu"), ("example please", "example"),
    ("Division next please", None), ("I want to learn fractions", None), ("20", None),
])
def test_classify(text, kind):
    assert conversation.classify(text) == kind


def test_number_words_and_wrapped_answers():
    assert conversation.number_from_words("ten") == "10"
    assert conversation.number_from_words("twenty-five") == "25"
    assert conversation.number_from_words("two hundred and fifty") == "250"
    assert conversation.number_from_words("one moment") is None
    assert conversation.unwrap_answer("is 10 correct?") == "10"
    assert conversation.unwrap_answer("10, is that right?") == "10"
    assert conversation.unwrap_answer("is it ten") == "ten"
    assert conversation.unwrap_answer("is photosynthesis a plant") is None


def test_greeting_and_help_get_a_menu_not_a_redirect(client):
    sid = start(client)
    for text in ("hello", "what can you do?", "which topics can I learn?", "thanks"):
        r = say(client, sid, text)
        assert r["action"] != "redirect" and "Percentages" in r["reply"], text


def test_greeting_during_a_question_repeats_it(client):
    sid = start(client)
    say(client, sid, "Teach me percentages")
    r = say(client, sid, "hello")
    assert "20% of 50" in r["reply"] and "10" not in r["reply"].replace("100", "")


def test_yes_after_done_moves_up_a_concept(client):
    sid = start(client)
    say(client, sid, "Teach me multiplication")
    assert say(client, sid, "20")["action"] == "done"
    r = say(client, sid, "yes")
    assert r["action"] == "ask" and r["concept_id"] == "division"


def test_concept_question_teaches_then_asks_without_leaking(client):
    sid = start(client)
    r = say(client, sid, "What is a percentage?")
    assert r["action"] == "explain" and r["concept_id"] == "percentages"
    assert "out of 100" in r["reply"] and "20% of 50" in r["reply"]
    assert say(client, sid, "10")["action"] == "done"


@pytest.mark.parametrize("answer", ["ten", "it is 10", "is 10 correct?", "My answer is 10", "10%"[:2]])
def test_answers_written_in_other_ways_are_graded(client, answer):
    sid = start(client)
    say(client, sid, "Teach me percentages")
    assert say(client, sid, answer)["action"] == "done"


def test_idk_gives_a_hint_then_explains_and_never_grades(client):
    sid = start(client)
    say(client, sid, "Teach me percentages")
    first = say(client, sid, "I don't know")
    assert first["action"] == "hint" and "out of how many" in first["reply"]
    second = say(client, sid, "idk")
    assert "Percent means out of 100" in second["reply"] and "10" not in second["reply"].replace("100", "")
    progress = client.get("/learners/l1/progress", params={"course_id": "ncert-maths"}).json()
    assert all(c["attempts"] == 0 for c in progress["concepts"])


def test_a_single_step_is_acknowledged_not_ignored(client):
    sid = start(client)
    say(client, sid, "Teach me percentages")
    r = say(client, sid, "20% means 20/100")
    assert r["action"] == "probe" and "step" in r["reply"]


def test_next_question_with_only_one_is_honest(client):
    sid = start(client)
    say(client, sid, "Teach me fractions")
    r = say(client, sid, "give me another question")
    assert "1/5 of 50" in r["reply"] and "Fractions" in r["reply"]
    assert say(client, sid, "give me an easier one")["concept_id"] == "division"


def test_unrecognised_message_lists_what_to_do(client):
    sid = start(client)
    say(client, sid, "Teach me percentages")
    r = say(client, sid, "banana smoothie recipe")
    assert "hint" in r["reply"] and "20% of 50" in r["reply"]
