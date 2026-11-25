"""Request and response models shared by the routers and services."""
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Action(str, Enum):
    """What the tutor controller decides to do next."""
    ASK = "ask"              # first diagnostic question on the learner's doubt
    EXPLAIN = "explain"      # explain an NCERT concept
    GUIDE = "guide"          # guide the next step of an NCERT exercise
    PROBE = "probe"          # probing question on the same concept
    HINT = "hint"            # hint, then ask again
    BACKTRACK = "backtrack"  # go down to a weak prerequisite
    ADVANCE = "advance"      # climb back up toward the learner's question
    DONE = "done"            # learner reached the answer
    REDIRECT = "redirect"    # off-topic or answer request; no learner-model update


class InputLabel(str, Enum):
    ON_TOPIC = "on_topic"
    OFF_TOPIC = "off_topic"
    ANSWER_REQUEST = "answer_request"


# ── Course pack ──────────────────────────────────────────────────────────────
class Question(BaseModel):
    id: str
    text: str
    answer: str
    hint: str = ""
    difficulty: int = 1


class Material(BaseModel):
    source: str
    page: str = ""
    text: str
    url: str = ""


class Concept(BaseModel):
    id: str
    name: str
    level: int
    prerequisites: list[str] = Field(default_factory=list)
    materials: list[Material] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)


class ConceptPublic(BaseModel):
    """A concept as learners see it: no questions, so the answer key never leaves the server."""
    id: str
    name: str
    level: int
    prerequisites: list[str] = Field(default_factory=list)
    materials: list[Material] = Field(default_factory=list)


class CoursePack(BaseModel):
    id: str
    title: str
    subject: str
    concepts: list[Concept]


class CourseSummary(BaseModel):
    id: str
    title: str
    subject: str
    concept_count: int


class GraphEdge(BaseModel):
    prerequisite: str
    concept: str


class CourseGraph(BaseModel):
    course_id: str
    nodes: list[ConceptPublic]
    edges: list[GraphEdge]


class GraphConcept(ConceptPublic):
    """A learning-graph concept. materials holds its evidence quotes with their NCERT citations; grade to
    chapter is where it is first quoted."""
    description: str = ""
    grade: int | None = None
    subject: str | None = None
    book_code: str | None = None
    chapter: int | None = None


class LearningGraphEdge(GraphEdge):
    confidence: float
    reason: str = ""
    evidence: Material | None = None


class LearningGraph(BaseModel):
    course_id: str
    run_id: str
    nodes: list[GraphConcept]
    edges: list[LearningGraphEdge]


# ── Sessions and chat ────────────────────────────────────────────────────────
class Chapter(BaseModel):
    grade: int = Field(ge=6, le=10)
    subject: Literal["maths", "science"]
    book_code: str = Field(min_length=1, max_length=80)
    chapter: int


class ChapterTopics(Chapter):
    title: str | None = None
    topics: list[str]


class SessionCreate(BaseModel):
    learner_id: str | None = None  # defaults to the signed-in username
    course_id: str
    grade: int | None = Field(default=None, ge=6, le=10)
    subject: Literal["maths", "science"] | None = None
    chapter: Chapter | None = None


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    new_topic: bool = False
    concept_id: str | None = Field(default=None, max_length=200)
    topic_heading: str | None = Field(default=None, min_length=1, max_length=2000)
    request_id: UUID | None = None


class Resource(BaseModel):
    source: str
    page: str = ""
    url: str = ""
    passage_id: str | None = None


class TutorReply(BaseModel):
    reply: str
    action: Action
    label: InputLabel
    concept_id: str | None = None
    level: int | None = None
    resource: Resource | None = None
    misconception: str | None = None   # unconfirmed suggestion: a rule name ("divides_by_the_percent") or one sentence
    wrong_step: int | None = None      # first wrong line of the learner's working (1-based), when working was sent
    chapter: Chapter | None = None
    generation: Literal["hosted", "extractive"] | None = None


class Turn(BaseModel):
    role: str  # "learner" or "tutor"
    text: str
    detail: TutorReply | None = None
    request_id: str | None = None


class SessionInfo(BaseModel):
    session_id: str
    learner_id: str
    course_id: str
    target_concept: str | None = None
    current_concept: str | None = None
    history: list[Turn] = Field(default_factory=list)


# ── Learner model ────────────────────────────────────────────────────────────
class AnswerIn(BaseModel):
    course_id: str
    session_id: str
    concept_id: str
    correct: bool


class ConceptProgress(BaseModel):
    concept_id: str
    name: str
    level: int
    attempts: int
    correct: int
    readiness: float


class Progress(BaseModel):
    learner_id: str
    course_id: str
    concepts: list[ConceptProgress]


# ── Search and practice ──────────────────────────────────────────────────────
class SearchHit(BaseModel):
    concept_id: str
    score: float
    material: Material
    chapter: Chapter | None = None
    passage_id: str | None = None


class PracticeRequest(BaseModel):
    course_id: str
    concept_id: str
    difficulty: int | None = None
    count: int = Field(default=3, ge=1, le=10)


class DiagnosticRequest(BaseModel):
    learner_id: str | None = None
    course_id: str
    per_concept: int = Field(default=1, ge=1, le=3)


class QuestionOut(BaseModel):
    """A question without its answer, safe to send to the learner."""
    id: str
    concept_id: str
    text: str
    hint: str = ""
    difficulty: int = 1


class AssessmentRequest(BaseModel):
    session_id: str
    kind: Literal["practice", "diagnostic"]
    concept_id: str | None = None
    difficulty: int | None = None


class AssessmentAnswer(BaseModel):
    text: str = Field(min_length=1, max_length=2000, pattern=r"\S")


class AssessmentResult(BaseModel):
    correct: bool
