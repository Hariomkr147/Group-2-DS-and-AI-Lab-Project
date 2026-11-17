"""Step finder: code checks the sums, the model names a wrong method, and nothing is invented."""
import pytest

from app.services import llm, step_finder as sf
from tests.test_api import say, start


class Fake:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def generate(self, prompt, system, max_tokens):
        self.prompts.append(prompt)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture()
def model(monkeypatch):
    def _model(reply):
        fake = Fake(reply)
        monkeypatch.setenv("STEP_FINDER_PROVIDER", "qwen_finetuned")
        monkeypatch.setattr(llm, "get_provider", lambda name=None: fake)
        return fake
    return _model


# ---------------------------------------------------------------- reading the message
@pytest.mark.parametrize("text, is_working", [
    ("2.5", False), ("x = 5", False), ("no idea", False), ("just tell me", False),
    ("50 / 20 = 2.5", True), ("I need 20% of 50\n50 ÷ 20 = 2.5", True), ("Plants eat soil\nSo roots feed it", True),
])
def test_split_working(text, is_working):
    assert (sf.split_working(text) is not None) == is_working


@pytest.mark.parametrize("lines, answer", [
    (["50 ÷ 20 = 2.5"], "2.5"), (["2x = 18", "x = 9"], "9"), (["= 2 × 19", "= 38 cm"], "38"),
    (["20 × 2.5 = 50", "Answer: Rs 50"], "50"), (["0.5 + 0.25 = 0.75", "= 3/4"], "3/4"),
    (["No new substance forms", "So it is a physical change"], "So it is a physical change"),
])
def test_final_answer(lines, answer):
    assert sf.final_answer(lines) == answer


# ---------------------------------------------------------------- arithmetic check
@pytest.mark.parametrize("lines, step", [
    (["15% = 15/100", "15/100 × 80 = 1200/100", "= 120"], 3),            # continuation line
    (["2x = 11 + 7", "2x = 17", "x = 8.5"], None),                        # letters: not checked by code
    (["Perimeter = 2 × (12 + 7)", "= 2 × 19", "= 36 cm"], 3),
    (["25% is one quarter", "60 ÷ 4 = 16"], 2),
    (["0.5 + 0.25 = 0.57"], 1),
    (["4 x 5 = 4 + 4 + 4 + 4 + 4", "= 18"], 2),
    (["50 ÷ 20 = 2.5", "Answer: 2.5"], None),                             # sums are right; the method is the problem
    (["10 ÷ 3 = 3.33"], None),                                            # rounding is not a slip
    (["1 / 0 = 5", "2(3+4) = 14", "__import__('os') = 1", "9**9**9 = 1"], None),   # unreadable lines are skipped
])
def test_arithmetic_slip(lines, step):
    assert sf.arithmetic_slip(lines) == step


# ---------------------------------------------------------------- model check
WORKING = ["I need 20% of 50", "50 ÷ 20 = 2.5", "Answer: 2.5"]


def test_model_names_the_wrong_step_from_the_answer_and_hint(model):
    fake = model('{"first_wrong_step": 2, "error": "Divided by the percent number."}')
    found = sf.find("What is 20% of 50?", "10", WORKING, hint="20% means 20 out of how many?")
    assert (found.step, found.line, found.error, found.source) == (2, "50 ÷ 20 = 2.5", "Divided by the percent number.", "model")
    assert "The correct final answer is 10" in fake.prompts[0] and "2. 50 ÷ 20 = 2.5" in fake.prompts[0]


@pytest.mark.parametrize("reply", [
    '{"first_wrong_step": 0, "error": ""}',          # model sees no error
    '{"first_wrong_step": 7, "error": "x"}',         # a step that does not exist
    "What does 20% mean?",                           # ignored the format
    RuntimeError("quota used up"),
])
def test_no_finding_when_the_model_gives_nothing_usable(model, reply):
    model(reply)
    assert sf.find("What is 20% of 50?", "10", WORKING) is None


def test_explanation_that_gives_the_answer_away_is_dropped(model):
    model('{"first_wrong_step": 2, "error": "It should be 10."}')
    found = sf.find("What is 20% of 50?", "10", WORKING)
    assert found.step == 2 and found.error == ""


def test_arithmetic_slip_wins_and_the_model_is_not_asked(model):
    fake = model('{"first_wrong_step": 1, "error": "wrong"}')
    found = sf.find("What is 25% of 60?", "15", ["25% is one quarter", "60 ÷ 4 = 16"])
    assert (found.step, found.source, fake.prompts) == (2, "arithmetic", [])


def test_model_off_leaves_only_the_arithmetic_check(monkeypatch):
    monkeypatch.setenv("STEP_FINDER_PROVIDER", "none")
    monkeypatch.setattr(llm, "get_provider", lambda name=None: pytest.fail("model must not be called"))
    assert sf.find("What is 20% of 50?", "10", WORKING) is None


# ---------------------------------------------------------------- in the tutor
def test_tutor_asks_for_working_then_points_at_the_step(client, model):
    sid = start(client)
    assert say(client, sid, "help me with multiplication")["action"] == "ask"       # What is 4 x 5?
    r = say(client, sid, "9")
    assert r["action"] == "hint" and "Show your steps" in r["reply"] and r["wrong_step"] is None

    model('{"first_wrong_step": 1, "error": "Added the two numbers instead of multiplying."}')
    r = say(client, sid, "4 + 5 = 9")
    assert r["action"] == "hint" and r["wrong_step"] == 1 and r["reply"].startswith("Look again at step 1")
    assert r["misconception"] == "Added the two numbers instead of multiplying." and "20" not in r["reply"]

    r = say(client, sid, "4 x 5 = 4 + 4 + 4 + 4 + 4\n= 18")                          # right method, slip in the sum
    assert r["wrong_step"] == 2 and "check the arithmetic" in r["reply"] and r["misconception"] is None

    r = say(client, sid, "4 + 4 + 4 + 4 + 4 = 20")                                   # working that ends on the answer
    assert r["action"] == "done" and r["wrong_step"] is None


def test_working_is_graded_once_and_bare_answers_behave_as_before(client):
    sid = start(client)
    say(client, sid, "help me with multiplication")
    say(client, sid, "4 + 5 = 9")
    say(client, sid, "20")
    prog = client.get("/learners/l1/progress", params={"course_id": "ncert-maths"}).json()
    mul = next(c for c in prog["concepts"] if c["concept_id"] == "multiplication")
    assert mul["attempts"] == 2 and mul["correct"] == 1
