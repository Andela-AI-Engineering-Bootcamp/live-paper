"""FastAPI application factory — pattern from zeya-antenatal.

create_app() is the single entry point for constructing the application.
Called once at module load for uvicorn, and once per test run for isolation.
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, escalation, expert_responses, experts, health, papers, search
from app.services.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("LivePaper API starting up")
    # In dev (no AURORA_CLUSTER_ARN) this creates SQLite tables; in prod it is
    # a no-op because schema is owned by alembic, run from the container CMD.
    await init_db()
    yield
    logger.info("LivePaper API shut down")


def create_app() -> FastAPI:
    debug = os.getenv("DEBUG", "true").lower() == "true"

    app = FastAPI(
        title="LivePaper API",
        version="0.1.0",
        description="Turns static research papers into live, conversational documents with expert escalation.",
        lifespan=lifespan,
        docs_url="/docs" if debug else None,
        redoc_url=None,
    )

    #cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = "/api"
    app.include_router(health.router, prefix=prefix)
    app.include_router(papers.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(escalation.router, prefix=prefix)
    app.include_router(experts.router, prefix=prefix)
    app.include_router(expert_responses.router, prefix=prefix)
    app.include_router(chat.router)  # /chat (no /api prefix — matches frontend)

    @app.get("/")
    async def root() -> dict:
        return {"service": "livepaper-api", "status": "ok", "docs": "/docs"}

    return app

