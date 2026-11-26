"""NCERT skill level: the tutor's reply is judged in the background, recorded, and shown on a 1 to 10 scale."""
from app.db import CourseRow, SessionLocal, SessionRow
from app.services import llm, ncert, socratic, tutor


class _FakeModel:
    def __init__(self, label):
        self.label = label

    def generate(self, prompt, system, max_tokens):
        return self.label


def test_judge_reads_the_model_label(monkeypatch):
    monkeypatch.setenv("MESSAGE_CLASSIFIER_PROVIDER", "fake")
    for label, verdict in (("correct", True), ("Incorrect.", False), ("none", None), ("maybe", None)):
        monkeypatch.setattr(llm, "get_provider", lambda name, label=label: _FakeModel(label))
        assert socratic.judge_attempt("It is 12.", "Yes, 12 is right. Well done!") is verdict


def test_judge_is_off_without_a_model(monkeypatch):
    monkeypatch.setenv("MESSAGE_CLASSIFIER_PROVIDER", "templates")
    assert socratic.judge_attempt("It is 12.", "Yes, that's right.") is None


def _ncert_session(learner="l1"):
    with SessionLocal() as db:
        if db.get(CourseRow, ncert.COURSE_ID) is None:
            db.add(CourseRow(id=ncert.COURSE_ID, title="NCERT", subject="maths and science"))
        db.add(SessionRow(id="s1", learner_id=learner, course_id=ncert.COURSE_ID, stack=[], tries=0, pending=None))
        db.commit()


def _item(correct_word, concept="7-maths-gegp1-8"):
    return {"learner_id": "l1", "course_id": ncert.COURSE_ID, "session_id": "s1", "concept_id": concept,
            "student": "my answer", "tutor": correct_word, "problem": ""}


def test_skill_level_from_judged_answers(client, monkeypatch):
    monkeypatch.delenv("KT_MODEL", raising=False)                 # smoothed accuracy, no torch needed
    _ncert_session()
    empty = client.get("/learners/l1/skill", params={"grade": 7, "subject": "maths"}).json()
    assert empty["level"] is None and empty["answers"] == 0

    verdicts = {"right": True, "wrong": False, "unclear": None}
    monkeypatch.setattr(socratic, "judge_attempt", lambda student, reply, problem="": verdicts[reply])
    tutor.judge_and_record([_item("right"), _item("right"), _item("wrong"), _item("unclear")])

    skill = client.get("/learners/l1/skill", params={"grade": 7, "subject": "maths"}).json()
    # 2 right of 3 judged (the unclear one is not recorded): (2 + 1) / (3 + 2) = 0.6 -> 1 + 9 * 0.6 = 6.4 -> 6
    assert skill == {"grade": 7, "subject": "maths", "level": 6, "source": "accuracy", "answers": 3, "correct": 2}
    other = client.get("/learners/l1/skill", params={"grade": 7, "subject": "science"}).json()
    assert other["level"] is None                                  # classes and subjects never mix


def test_skill_rejects_unknown_class(client):
    assert client.get("/learners/l1/skill", params={"grade": 5, "subject": "maths"}).status_code == 422
