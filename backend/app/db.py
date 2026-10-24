"""PostgreSQL connection and table definitions (SQLAlchemy 2.0).

Set DATABASE_URL to change the database; the default matches docker-compose.yml.
Tables are created at startup; add Alembic migrations once the schema settles.
"""
import os
from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, Index, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://tutor:tutor@localhost:5432/tutor")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    """FastAPI dependency: one database session per request."""
    with SessionLocal() as db:
        yield db


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CourseRow(Base):
    __tablename__ = "courses"
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    subject: Mapped[str]


class ConceptRow(Base):
    __tablename__ = "concepts"
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    level: Mapped[int]
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    materials: Mapped[list] = mapped_column(JSON, default=list)
    questions: Mapped[list] = mapped_column(JSON, default=list)


class SessionRow(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(primary_key=True)
    learner_id: Mapped[str] = mapped_column(index=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    target_concept: Mapped[str | None]
    current_concept: Mapped[str | None]
    pending: Mapped[dict | None] = mapped_column(JSON, default=None)  # question being answered
    stack: Mapped[list] = mapped_column(JSON, default=list)           # concepts to climb back to
    tries: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class TurnRow(Base):
    __tablename__ = "turns"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str]
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=_now)


class AnswerRow(Base):
    """One learner answer. History is per learner and per course; the session is kept for DKT input."""
    __tablename__ = "answers"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    learner_id: Mapped[str]
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    concept_id: Mapped[str]
    correct: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(default=_now)

    __table_args__ = (Index("ix_answers_learner_course", "learner_id", "course_id"),)
