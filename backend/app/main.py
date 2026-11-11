"""Socratic AI Tutor backend.

Start PostgreSQL (docker compose up -d), then from the backend folder:
    uv run uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs

Every route except /health and /auth/* needs a bearer token (see app/security.py).
"""
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, CourseRow, SessionLocal, engine
from .routers import auth, courses, learners, practice, search, sessions
from .sample_pack import SAMPLE_PACK
from .security import check_config, current_user
from .services import course_store

PRODUCTION = os.environ.get("APP_ENV") == "production"


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_config()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.get(CourseRow, SAMPLE_PACK.id) is None:  # development data; real packs come from POST /courses
            course_store.add_pack(db, SAMPLE_PACK)
    yield


# The API reference is hidden in production.
app = FastAPI(title="Socratic AI Tutor", version="0.2.0", lifespan=lifespan,
              docs_url=None if PRODUCTION else "/docs", redoc_url=None, openapi_url=None if PRODUCTION else "/openapi.json")

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if not request.url.path.startswith("/docs"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(auth.router)  # /auth/login is the only open route besides /health
for r in (sessions.router, learners.router, courses.router, search.router, practice.router):
    app.include_router(r, dependencies=[Depends(current_user)])


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
