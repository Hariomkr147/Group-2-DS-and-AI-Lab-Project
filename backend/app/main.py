"""Socratic AI Tutor backend.

Start PostgreSQL (docker compose up -d), then from the backend folder:
    uv run uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs

Every route except /health and /auth/* needs a bearer token (see app/security.py).
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .db import Base, CourseRow, SessionLocal, engine
from .routers import auth, courses, learners, llm, practice, search, sessions
from .sample_pack import SAMPLE_PACK
from .security import check_config, current_user
from .services import course_store, ncert

PRODUCTION = os.environ.get("APP_ENV") == "production"
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_config()
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.get(CourseRow, SAMPLE_PACK.id) is None:  # development data; real packs come from POST /courses
            course_store.add_pack(db, SAMPLE_PACK)
        if ncert.configured() and db.get(CourseRow, ncert.COURSE_ID) is None:
            db.add(CourseRow(id=ncert.COURSE_ID, title=ncert.COURSE_TITLE, subject="maths and science"))
            db.commit()
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


api_router = APIRouter(prefix="/api")
app.include_router(auth.router)  # /auth/login is the only open route besides /health
api_router.include_router(auth.router)

for r in (sessions.router, learners.router, courses.router, search.router, practice.router, llm.router):
    app.include_router(r, dependencies=[Depends(current_user)])
    api_router.include_router(r, dependencies=[Depends(current_user)])

app.include_router(api_router)

if FRONTEND_DIST.exists() and (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse, tags=["ui"])
def index():
    """Serve the complete Socratic AI Tutor Web UI."""
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        return HTMLResponse(content=(FRONTEND_DIST / "index.html").read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Socratic AI Tutor API is running. Visit <a href='/docs'>/docs</a>.</h1>")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
