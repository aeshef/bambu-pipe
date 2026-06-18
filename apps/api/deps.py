"""Shared FastAPI dependencies."""

from __future__ import annotations

from bambu_pipe.config import Settings
from bambu_pipe.orchestrator import PipelineOrchestrator
from fastapi import Request


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_orchestrator(request: Request) -> PipelineOrchestrator:
    return request.app.state.orchestrator
