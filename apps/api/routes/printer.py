"""Printer endpoints."""

from __future__ import annotations

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import BambuPipeError
from bambu_pipe.printer.client import BambuPrinterClient
from fastapi import APIRouter, Depends, HTTPException

from apps.api.deps import get_settings

router = APIRouter(prefix="/printer", tags=["printer"])


@router.get("/status")
async def printer_status(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    client = BambuPrinterClient()
    try:
        return await client.status(settings)
    except BambuPipeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
