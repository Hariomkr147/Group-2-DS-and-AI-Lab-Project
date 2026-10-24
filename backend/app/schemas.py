"""Request and response models shared by the routers and services."""
from enum import Enum

from pydantic import BaseModel, Field


class Action(str, Enum):
    """What the tutor controller decides to do next."""
    ASK = "ask"              # first diagnostic question on the learner's doubt
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
    nodes: list[Concept]
    edges: list[GraphEdge]


# ── Sessions and chat ────────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    learner_id: str
    course_id: str


class Turn(BaseModel):
    role: str  # "learner" or "tutor"
    text: str


class SessionInfo(BaseModel):
    session_id: str
    learner_id: str
    course_id: str
    target_concept: str | None = None
    current_concept: str | None = None
    history: list[Turn] = Field(default_factory=list)


class MessageIn(BaseModel):
    text: str = Field(min_length=1)


class Resource(BaseModel):
    source: str
    page: str = ""
    url: str = ""


class TutorReply(BaseModel):
    reply: str
    action: Action
    label: InputLabel
    concept_id: str | None = None
    level: int | None = None
    resource: Resource | None = None


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


class PracticeRequest(BaseModel):
    course_id: str
    concept_id: str
    difficulty: int | None = None
    count: int = Field(default=3, ge=1, le=10)


class DiagnosticRequest(BaseModel):
    learner_id: str
    course_id: str
    per_concept: int = Field(default=1, ge=1, le=3)


class QuestionOut(BaseModel):
    """A question without its answer, safe to send to the learner."""
    id: str
    concept_id: str
    text: str
    hint: str = ""
    difficulty: int = 1
