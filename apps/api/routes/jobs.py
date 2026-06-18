"""Job endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import BambuPipeError
from bambu_pipe.models.job import PipelineMode, PrintJob
from bambu_pipe.orchestrator import PipelineOrchestrator
from bambu_pipe.paths import job_staging_dir
from bambu_pipe.stages.validate import SUPPORTED_MODEL_SUFFIXES
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from apps.api.deps import get_orchestrator, get_settings

router = APIRouter(prefix="/jobs", tags=["jobs"])
UPLOAD_CHUNK_SIZE = 1024 * 1024


class JobCreateRequest(BaseModel):
    mode: PipelineMode = "mesh_only"
    prompt: str = ""
    model_path: str | None = None
    quality: str = "standard"
    material: str | None = None
    auto_approve: bool = False


class ApprovalRequest(BaseModel):
    approved: bool = True


def _serialize_job(job: PrintJob) -> dict[str, object]:
    validation = job.artifacts.validation
    return {
        "id": job.id,
        "stage": job.stage.value,
        "mode": job.mode,
        "prompt": job.prompt,
        "quality": job.quality,
        "material": job.material,
        "auto_approve": job.auto_approve,
        "error": job.error,
        "artifacts": {
            "model_path": job.artifacts.model_path,
            "sliced_path": job.artifacts.sliced_path,
            "thumbnail_path": job.artifacts.thumbnail_path,
            "estimated_print_time": job.artifacts.estimated_print_time,
            "estimated_filament_g": job.artifacts.estimated_filament_g,
            "remote_filename": job.artifacts.remote_filename,
            "validation": validation.model_dump() if validation else None,
        },
        "awaits_approval": job.awaits_approval,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


async def _create_upload_job(
    *,
    file: UploadFile,
    quality: str,
    material: str | None,
    auto_approve: bool,
    orchestrator: PipelineOrchestrator,
    settings: Settings,
) -> PrintJob:
    suffix = Path(file.filename or "model.stl").suffix or ".stl"
    if suffix.lower() not in SUPPORTED_MODEL_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_MODEL_SUFFIXES))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model format: {suffix}. Supported: {supported}",
        )

    staging = job_staging_dir(settings.staging_dir, f"upload-{uuid.uuid4().hex[:8]}")
    destination = staging / f"upload{suffix}"
    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    with destination.open("wb") as handle:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            written += len(chunk)
            if written > max_bytes:
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"Upload exceeds BAMBU_PIPE_MAX_UPLOAD_MB={settings.max_upload_mb}",
                )
            handle.write(chunk)

    return await orchestrator.create_job(
        mode="mesh_only",
        model_path=str(destination),
        quality=quality,
        material=material,
        auto_approve=auto_approve,
    )


@router.post("")
async def create_job(
    payload: JobCreateRequest,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    if payload.model_path is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "model_path is disabled in the REST API for safety. "
                "Use POST /jobs/upload or a trusted internal adapter."
            ),
        )
    try:
        job = await orchestrator.create_job(
            mode=payload.mode,
            prompt=payload.prompt,
            model_path=None,
            quality=payload.quality,
            material=payload.material,
            auto_approve=payload.auto_approve,
        )
    except BambuPipeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_job(job)


@router.post("/upload")
async def create_job_from_upload(
    file: UploadFile,
    quality: str = "standard",
    material: str | None = None,
    auto_approve: bool = False,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    job = await _create_upload_job(
        file=file,
        quality=quality,
        material=material,
        auto_approve=auto_approve,
        orchestrator=orchestrator,
        settings=settings,
    )
    return _serialize_job(job)


@router.post("/print")
async def print_uploaded_model(
    file: UploadFile,
    quality: str = "standard",
    material: str | None = None,
    auto_approve: bool = False,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    job = await _create_upload_job(
        file=file,
        quality=quality,
        material=material,
        auto_approve=auto_approve,
        orchestrator=orchestrator,
        settings=settings,
    )
    try:
        job = await orchestrator.run_mesh_pipeline(job.id)
    except BambuPipeError as exc:
        job = await orchestrator.get_job(job.id)
        detail = {"error": str(exc), "job": _serialize_job(job) if job else None}
        raise HTTPException(status_code=409, detail=detail) from exc
    return _serialize_job(job)


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, object]:
    job = await orchestrator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(job)


@router.get("/{job_id}/preview")
async def get_job_preview(
    job_id: str,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, object]:
    job = await orchestrator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    validation = job.artifacts.validation
    checks = validation.checks if validation else []
    return {
        "id": job.id,
        "stage": job.stage.value,
        "material": job.material,
        "quality": job.quality,
        "confidence_score": validation.score if validation else None,
        "validation_passed": validation.passed if validation else None,
        "checks": [check.model_dump() for check in checks],
        "estimated_print_time": job.artifacts.estimated_print_time,
        "estimated_filament_g": job.artifacts.estimated_filament_g,
        "has_model": job.artifacts.model_path is not None,
        "has_slice": job.artifacts.sliced_path is not None,
        "thumbnail_path": job.artifacts.thumbnail_path,
        "summary": validation.to_summary() if validation else "Validation has not run yet",
    }


@router.post("/{job_id}/run")
async def run_job(
    job_id: str,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, object]:
    try:
        job = await orchestrator.run_mesh_pipeline(job_id)
    except BambuPipeError as exc:
        job = await orchestrator.get_job(job_id)
        detail = {"error": str(exc), "job": _serialize_job(job) if job else None}
        raise HTTPException(status_code=409, detail=detail) from exc
    return _serialize_job(job)


@router.post("/{job_id}/approve")
async def approve_job(
    job_id: str,
    payload: ApprovalRequest,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, object]:
    job = await orchestrator.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.awaits_approval:
        raise HTTPException(status_code=409, detail="Job is not awaiting approval")

    if not payload.approved:
        job = await orchestrator.cancel(job_id)
        return _serialize_job(job)

    next_stage = orchestrator.stage_after_approval(job.stage)
    job.advance(next_stage)
    await orchestrator.store.save(job)

    try:
        job = await orchestrator.run_mesh_pipeline(job_id)
    except BambuPipeError as exc:
        job = await orchestrator.get_job(job_id)
        detail = {"error": str(exc), "job": _serialize_job(job) if job else None}
        raise HTTPException(status_code=409, detail=detail) from exc
    return _serialize_job(job)


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> dict[str, object]:
    job = await orchestrator.cancel(job_id)
    return _serialize_job(job)
