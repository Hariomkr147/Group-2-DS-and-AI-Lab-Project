from app.services import misconception as m


def setup_function():
    m.reset_history()


def test_percent_error_uses_the_questions_own_numbers():
    assert m.detect("What is 30% of 70?", "7/3", "21") == "divides_by_the_percent"
    assert m.detect("What is 12% of 150?", "12.5", "18") == "divides_by_the_percent"


def test_unknown_error_is_not_guessed():
    assert m.detect("What is 30% of 70?", "2.3333", "21") is None


def test_correct_or_unreadable_answer_is_not_flagged():
    assert m.detect("What is 20% of 50?", "10", "10") is None
    assert m.detect("What is 20% of 50?", "no idea", "10") is None


def test_search_names_a_wrong_operation_in_an_unseen_question():
    d = m.diagnose("A train covers 150 km in 3 hours. What is its speed in km/h?", "450", "50")
    assert d.name == "multiplies_instead_of_dividing" and d.source == "search"


def test_repeated_error_is_recurring_and_more_confident():
    first = m.diagnose("What is 20% of 50?", "2.5", "10", "kid")
    again = m.diagnose("What is 15% of 60?", "4", "9", "kid")
    assert not first.recurring and again.recurring and again.confidence > first.confidence


# ---------------------------------------------------------------- third layer: the Socratic model
import json

import pytest

from app.services import llm, socratic


class FakeModel:
    def __init__(self, reply):
        self.reply = reply

    def generate(self, prompt, system, max_tokens):
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture()
def model(monkeypatch):
    def _model(reply):
        monkeypatch.setenv("SOCRATIC_PROVIDER", "qwen_finetuned")
        monkeypatch.setattr(llm, "get_provider", lambda name=None: FakeModel(reply))
    return _model


def reply(calculation, sentence):
    return json.dumps({"calculation": calculation, "misconception": sentence})


def test_model_layer_is_off_with_templates():
    assert socratic.diagnose_misconception("Find the area of a 4 by 6 rectangle.", "20", "24") is None


def test_model_suggestion_kept_when_its_calculation_gives_the_learners_answer(model):
    model(reply("2 * (4 + 6)", "Finds the perimeter instead of the area."))
    assert socratic.diagnose_misconception("Find the area of a 4 by 6 rectangle.", "20", "24") \
        == "Finds the perimeter instead of the area."


@pytest.mark.parametrize("calculation", [
    "4 + 6",          # gives 10, not the learner's 20
    "20",             # no calculation, just the answer
    "5 * 4",          # 5 is not a number in the problem
    "",               # nothing to check
])
def test_model_suggestion_dropped_when_the_calculation_does_not_check_out(model, calculation):
    model(reply(calculation, "Finds the perimeter instead of the area."))
    assert socratic.diagnose_misconception("Find the area of a 4 by 6 rectangle.", "20", "24") is None


def test_non_numeric_answer_keeps_the_unchecked_suggestion(model):
    model(reply("", "Thinks plants take their food from the soil."))
    assert socratic.diagnose_misconception("How do plants get their food?", "from the soil", "photosynthesis") \
        == "Thinks plants take their food from the soil."


@pytest.mark.parametrize("answer", [
    "not json at all",
    reply("", ""),
    reply("", "The answer is photosynthesis, not soil."),      # gives the correct answer away
    reply("", "x" * 300),                                        # too long to be one sentence
    RuntimeError("model down"),
])
def test_unusable_model_reply_gives_nothing(model, answer):
    model(answer)
    assert socratic.diagnose_misconception("How do plants get their food?", "from the soil", "photosynthesis") is None
