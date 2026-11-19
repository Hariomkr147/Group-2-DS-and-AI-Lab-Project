import pytest

from app.services import akt, learner_model

torch = pytest.importorskip("torch")


@pytest.fixture()
def tracer(monkeypatch):
    monkeypatch.setenv("KT_MODEL", "akt")
    monkeypatch.setattr(akt, "_tracer", None)
    monkeypatch.setattr(akt, "_tried", False)
    t = akt.get_tracer()
    assert t is not None
    return t


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("KT_MODEL", raising=False)
    assert akt.get_tracer() is None


def test_predicts_only_mapped_concepts(tracer):
    history = [("percentages", True), ("percentages", True), ("division", False)]
    p = tracer.predict("percentages", history)
    assert 0.0 < p < 1.0
    assert tracer.predict("division", history) is None          # unmapped concept: no guessed skill
    assert tracer.predict("percentages", [("division", True)]) is None  # no mapped history yet


def test_more_correct_answers_raise_readiness(tracer):
    wrong = tracer.predict("percentages", [("percentages", False)] * 6)
    right = tracer.predict("percentages", [("percentages", True)] * 6)
    assert right > wrong


def test_bad_checksum_falls_back(monkeypatch):
    monkeypatch.setenv("KT_MODEL", "akt")
    monkeypatch.setattr(akt, "_tracer", None)
    monkeypatch.setattr(akt, "_tried", False)
    monkeypatch.setattr(akt, "WEIGHTS_SHA256", "0" * 64)
    assert akt.get_tracer() is None


def test_readiness_uses_akt_then_falls_back(tracer, monkeypatch):
    monkeypatch.setattr(learner_model, "history", lambda *a: [("percentages", True)] * 4)
    assert learner_model.readiness(None, "l", "c", "percentages") == tracer.predict("percentages", [("percentages", True)] * 4)
    # unmapped concept: smoothed accuracy path (no database needed once stats is stubbed)
    monkeypatch.setattr(learner_model, "stats", lambda *a: (2, 1))
    assert learner_model.readiness(None, "l", "c", "division") == 0.5
