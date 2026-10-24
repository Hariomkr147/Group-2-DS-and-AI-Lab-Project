"""Socratic AI Tutor backend.

Start PostgreSQL (docker compose up -d), then from the backend folder:
    uv run uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, CourseRow, SessionLocal, engine
from .routers import courses, learners, practice, search, sessions
from .sample_pack import SAMPLE_PACK
from .services import course_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.get(CourseRow, SAMPLE_PACK.id) is None:  # development data; real packs come from POST /courses
            course_store.add_pack(db, SAMPLE_PACK)
    yield


app = FastAPI(title="Socratic AI Tutor", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

for r in (sessions.router, learners.router, courses.router, search.router, practice.router):
    app.include_router(r)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
