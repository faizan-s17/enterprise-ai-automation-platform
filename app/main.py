"""Enterprise AI Automation Platform, application entry point."""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
log = logging.getLogger("platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from app.seed import seed_if_empty

    seed_if_empty()
    log.info(
        "%s %s ready (env=%s, ai=%s)",
        settings.APP_NAME, settings.VERSION, settings.ENVIRONMENT,
        "configured" if settings.ai_enabled else "local fallback",
    )
    yield


DESCRIPTION = """
Centralised automation platform connecting business systems, automating
repetitive work, and applying AI to documents, tickets, and reporting.

**Authentication.** Call `POST /api/v1/auth/login` with an email and password,
then send `Authorization: Bearer <access_token>`. In this page, use the
**Authorize** button.

**Roles.** `viewer` reads, `analyst` creates and processes, `manager` approves
and generates reports, `admin` manages users and reads the audit log. Roles are
hierarchical, so an admin satisfies every lower requirement.

**AI.** Every AI feature falls back to a deterministic local implementation
when no API key is configured, so the platform stays fully functional. The
`ai_enabled` flag on `/admin/stats` reports which mode is active.
"""

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.1f}"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log the detail, return a generic message.

    Stack traces and driver errors can carry table names and connection
    strings, which should not reach an API client.
    """
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. "
                           "The incident has been logged."},
    )


app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["Meta"])
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "api": settings.API_PREFIX,
    }


@app.get("/health", tags=["Meta"])
def health():
    """Liveness probe for Docker and the cloud platform."""
    from sqlalchemy import text

    from app.database import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:
        log.error("Health check database probe failed: %s", exc)
        database = "unavailable"

    healthy = database == "ok"
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "healthy" if healthy else "degraded",
            "version": settings.VERSION,
            "database": database,
            "ai": "configured" if settings.ai_enabled else "local-fallback",
        },
    )
