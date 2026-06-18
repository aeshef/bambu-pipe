"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from bambu_pipe.config import load_settings
from bambu_pipe.orchestrator import PipelineOrchestrator
from bambu_pipe.storage.sqlite import SQLiteJobStore
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.settings = settings
    app.state.orchestrator = PipelineOrchestrator(
        settings,
        store=SQLiteJobStore(settings.database_path),
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="bambu-pipe",
        version="0.1.0",
        description="Headless mesh-to-print pipeline for Bambu Lab printers",
        lifespan=lifespan,
    )

    from apps.api.routes import health, jobs, printer  # noqa: PLC0415

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(printer.router, prefix="/api/v1")
    return app
