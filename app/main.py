"""
FastAPI application entry-point.

Creates the app, wires up CORS, routers, static files, and startup
logic (DB init + default owner account).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.auth import hash_password
from app.config import settings
from app.database import async_session, init_db
from app.models import Admin
from app.routes import auth_routes, key_routes, stats_routes, user_routes, validate_routes

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook.

    On startup:
    1. Create all database tables.
    2. Seed a default ``owner`` account when no users exist.
    """
    # ── Startup ─────────────────────────────────────────────────────────
    await init_db()
    logger.info("Database tables created / verified.")

    # Seed default owner if the table is empty
    async with async_session() as session:
        result = await session.execute(select(Admin))
        if result.scalars().first() is None:
            default_owner = Admin(
                username=settings.ADMIN_USERNAME,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="owner",
                created_by="system",
            )
            session.add(default_owner)
            await session.commit()
            logger.info(
                "Default owner account created: username=%s",
                settings.ADMIN_USERNAME,
            )
        else:
            logger.info("At least one user exists — skipping default owner creation.")

    yield

    # ── Shutdown ────────────────────────────────────────────────────────
    logger.info("Application shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A production-ready API for generating, managing, and validating "
        "software license keys with role-based access control."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(key_routes.router)
app.include_router(validate_routes.router)
app.include_router(stats_routes.router)


# ── Static files ────────────────────────────────────────────────────────────
# Ensure the static directory exists so the mount never fails
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Root & health ───────────────────────────────────────────────────────────


@app.get("/", include_in_schema=False)
async def root():
    """Serve the front-end SPA if ``index.html`` exists, otherwise return
    a simple JSON greeting."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"message": f"Welcome to {settings.APP_NAME}"})


@app.get("/api/health", tags=["Health"])
async def health_check() -> dict:
    """Lightweight health-check endpoint for uptime monitors."""
    return {"status": "healthy", "app": settings.APP_NAME}
