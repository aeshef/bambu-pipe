"""Health and doctor endpoints."""

from __future__ import annotations

from bambu_pipe import __version__
from bambu_pipe.config import Settings
from bambu_pipe.doctor import run_doctor
from fastapi import APIRouter, Depends

from apps.api.deps import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/doctor")
async def doctor(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    report = run_doctor(settings)
    return {
        "ok": report.ok,
        "checks": [
            {
                "name": check.name,
                "ok": check.ok,
                "message": check.message,
                "suggestion": check.suggestion,
            }
            for check in report.checks
        ],
    }
