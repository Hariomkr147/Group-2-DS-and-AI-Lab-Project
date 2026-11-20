"""The Socratic model writes hint and probe turns; every failure falls back to the template."""
import pytest

from app.schemas import Action, Concept, Question
from app.services import llm, socratic

CONCEPT = Concept(id="pct", name="Percentages", level=4)
QUESTION = Question(id="pct-1", text="What is 20% of 50?", answer="10", hint="20% means 20 out of 100.")
TEMPLATE = socratic._template(Action.HINT, CONCEPT, QUESTION)


class Fake:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def generate(self, prompt, system, max_tokens):
        self.calls.append((prompt, system))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture()
def use(monkeypatch):
    def _use(reply, provider="qwen_finetuned"):
        fake = Fake(reply)
        monkeypatch.setenv("SOCRATIC_PROVIDER", provider)
        monkeypatch.setattr(llm, "get_provider", lambda name=None: fake)
        return fake
    return _use


def test_templates_when_the_model_is_switched_off(monkeypatch):
    monkeypatch.setenv("SOCRATIC_PROVIDER", "templates")
    monkeypatch.setattr(llm, "get_provider", lambda name=None: pytest.fail("model must not be called"))
    assert socratic.write(Action.HINT, CONCEPT, QUESTION, "2.5") == TEMPLATE


def test_fine_tuned_qwen_is_the_default(monkeypatch):
    asked = []
    monkeypatch.delenv("SOCRATIC_PROVIDER", raising=False)
    monkeypatch.setattr(llm, "get_provider", lambda name=None: asked.append(name) or Fake("What does 20% mean?"))
    assert socratic.write(Action.HINT, CONCEPT, QUESTION, "2.5") == "What does 20% mean?"
    assert asked == ["qwen_finetuned"]


def test_default_without_settings_falls_back_to_the_template(monkeypatch):
    monkeypatch.delenv("SOCRATIC_PROVIDER", raising=False)
    monkeypatch.delenv("QWEN_URL", raising=False)
    assert socratic.write(Action.HINT, CONCEPT, QUESTION, "2.5") == TEMPLATE


def test_model_writes_hint_with_the_training_prompt(use):
    fake = use("What does 20% mean as a fraction?")
    assert socratic.write(Action.HINT, CONCEPT, QUESTION, "2.5") == "What does 20% mean as a fraction?"
    prompt, system = fake.calls[0]
    assert prompt == "2.5" and "Problem: What is 20% of 50?" in system and "never reveal it): 10" in system


def test_new_question_turns_keep_the_template(use):
    fake = use("anything")
    assert socratic.write(Action.ASK, CONCEPT, QUESTION, "help with percentages") == \
        socratic._template(Action.ASK, CONCEPT, QUESTION)
    assert fake.calls == []


@pytest.mark.parametrize("reply", [
    "The answer is 10.",                       # gives the answer away
    "",                                        # empty
    "What does 20% mean as a",                 # cut off with no complete sentence
    RuntimeError("model is down"),
])
def test_bad_replies_fall_back_to_the_template(use, reply):
    use(reply)
    assert socratic.write(Action.HINT, CONCEPT, QUESTION, "2.5") == TEMPLATE


def test_cut_off_reply_keeps_complete_sentences(use):
    use("Good try. What does 20% mean? Now think about how")
    assert socratic.write(Action.PROBE, CONCEPT, QUESTION, "2.5") == "Good try. What does 20% mean?"


class _Response:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        data = self.text.encode()
        return data if size < 0 else data[:size]


@pytest.mark.parametrize("stream, expected", [
    ('event: heartbeat\ndata: null\n\nevent: complete\ndata: ["What does 20% mean?"]\n\n', "What does 20% mean?"),
    ('event: error\ndata: {"error": "GPU quota exceeded"}\n\n', RuntimeError),
])
def test_qwen_finetuned_reads_a_hugging_face_space(monkeypatch, stream, expected):
    import urllib.request
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.data, request.get_header("Authorization")))
        return _Response('{"event_id": "abc"}' if request.data else stream)

    monkeypatch.setenv("QWEN_URL", "https://someone-demo.hf.space/")
    monkeypatch.setenv("QWEN_API_KEY", "token")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    if expected is RuntimeError:
        with pytest.raises(RuntimeError, match="quota"):
            llm.QwenFinetuned().generate("2.5", "system text", 96)
        return
    assert llm.QwenFinetuned().generate("2.5", "system text", 96) == expected
    assert calls[0][0] == "https://someone-demo.hf.space/gradio_api/call/predict"
    assert b'"data": ["system text", "2.5"]' in calls[0][1]
    assert calls[1][0].endswith("/gradio_api/call/predict/abc") and calls[1][2] == "Bearer token"


def test_qwen_finetuned_provider_needs_its_settings(monkeypatch):
    monkeypatch.delenv("QWEN_URL", raising=False)
    with pytest.raises(Exception) as error:
        llm.QwenFinetuned().generate("hi", None, 96)
    assert "QWEN_URL" in str(error.value.detail)


def test_chat_uses_the_model_and_history(use):
    fake = use("Fair point, let me try a new angle. What is 1% of 50?")
    reply = socratic.chat(QUESTION, "same question again", [("tutor", "What is 20% of 50?")], "Be brief.")
    assert reply.startswith("Fair point")
    prompt, system = fake.calls[0]
    assert "Tutor: What is 20% of 50?" in prompt and "Student: same question again" in prompt and "Be brief." in system


@pytest.mark.parametrize("reply", ["It is 10.", "", "Tutor: hi", RuntimeError("down")])
def test_chat_falls_back_to_none(use, reply):
    use(reply)
    assert socratic.chat(QUESTION, "hmm", []) is None
