"""Pipeline orchestration."""

from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import BambuPipeError, JobError, ValidationFailedError
from bambu_pipe.models.job import JobStage, PipelineMode, PrintJob
from bambu_pipe.paths import job_staging_dir
from bambu_pipe.queue.printer_queue import PrinterQueue
from bambu_pipe.stages.generate import DefaultGenerationStage
from bambu_pipe.stages.print import DefaultPrintStage
from bambu_pipe.stages.slice import DefaultSliceStage
from bambu_pipe.stages.validate import DefaultValidationStage
from bambu_pipe.storage.base import JobStore
from bambu_pipe.storage.memory import MemoryJobStore

log = logging.getLogger(__name__)

ApprovalCallback = Callable[[PrintJob, str], Awaitable[bool]]


class PipelineOrchestrator:
    def __init__(
        self,
        settings: Settings,
        *,
        store: JobStore | None = None,
        printer_queue: PrinterQueue | None = None,
        validation_stage: DefaultValidationStage | None = None,
        generation_stage: DefaultGenerationStage | None = None,
        slice_stage: DefaultSliceStage | None = None,
        print_stage: DefaultPrintStage | None = None,
        request_approval: ApprovalCallback | None = None,
    ) -> None:
        self.settings = settings
        self.store = store or MemoryJobStore()
        self.printer_queue = printer_queue or PrinterQueue()
        self.validation_stage = validation_stage or DefaultValidationStage()
        self.generation_stage = generation_stage or DefaultGenerationStage()
        self.slice_stage = slice_stage or DefaultSliceStage()
        self.print_stage = print_stage or DefaultPrintStage()
        self.request_approval = request_approval
        self._approval_waiters: dict[str, asyncio.Future[bool]] = {}

    async def create_job(
        self,
        *,
        mode: PipelineMode = "mesh_only",
        prompt: str = "",
        model_path: str | None = None,
        quality: str | None = None,
        material: str | None = None,
        auto_approve: bool | None = None,
    ) -> PrintJob:
        if mode == "mesh_only" and not model_path:
            raise JobError("mesh_only mode requires model_path")

        if not model_path and not prompt:
            raise JobError("Provide either model_path or prompt")

        job = PrintJob(
            mode=mode,
            prompt=prompt,
            model_path=model_path,
            quality=quality or self.settings.quality,  # type: ignore[arg-type]
            material=material or self.settings.material,
            auto_approve=self.settings.auto_approve if auto_approve is None else auto_approve,
        )
        if model_path:
            staging = job_staging_dir(self.settings.staging_dir, job.id)
            destination = staging / Path(model_path).name
            shutil.copy2(model_path, destination)
            job.artifacts.model_path = str(destination)
        await self.store.save(job)
        return job

    async def resolve_approval(self, job_id: str, approved: bool) -> None:
        future = self._approval_waiters.pop(job_id, None)
        if future and not future.done():
            future.set_result(approved)

    async def approve(self, job_id: str) -> PrintJob:
        await self.resolve_approval(job_id, True)
        return await self._require_job(job_id)

    async def cancel(self, job_id: str) -> PrintJob:
        job = await self._require_job(job_id)
        if not job.is_terminal:
            job.advance(JobStage.CANCELLED)
            await self.store.save(job)
        await self.resolve_approval(job_id, False)
        return job

    async def get_job(self, job_id: str) -> PrintJob | None:
        return await self.store.get(job_id)

    async def list_jobs(self) -> list[PrintJob]:
        return await self.store.list()

    def stage_after_approval(self, stage: JobStage) -> JobStage:
        return self._stage_after_approval(stage)

    async def run_mesh_pipeline(self, job_id: str) -> PrintJob:
        job = await self._require_job(job_id)
        try:
            while not job.is_terminal:
                if job.stage == JobStage.PENDING:
                    if job.model_path or job.artifacts.model_path:
                        await self._run_validation(job)
                    elif job.mode == "text_full":
                        job.advance(JobStage.GENERATING)
                        await self.store.save(job)
                    else:
                        raise JobError(f"Cannot start job without model in mode {job.mode}")
                    continue

                if job.stage == JobStage.GENERATING:
                    await self._run_generation(job)
                    continue

                if job.stage == JobStage.AWAITING_MODEL_APPROVAL:
                    if await self._needs_approval(job):
                        return job
                    continue

                if job.stage == JobStage.VALIDATING:
                    await self._run_validation(job)
                    continue

                if job.stage == JobStage.AWAITING_VALIDATION_APPROVAL:
                    if await self._needs_approval(job):
                        return job
                    continue

                if job.stage == JobStage.SLICING:
                    await self._run_slice(job)
                    continue

                if job.stage == JobStage.AWAITING_SLICE_APPROVAL:
                    if await self._needs_approval(job):
                        return job
                    continue

                if job.stage == JobStage.UPLOADING:
                    await self.printer_queue.run(lambda: self._run_print(job))
                    await self.store.save(job)
                    return job

                if job.awaits_approval:
                    return job

                raise JobError(f"Cannot resume pipeline from stage {job.stage.value}")
        except BambuPipeError as exc:
            job.advance(JobStage.FAILED, error=str(exc))
            await self.store.save(job)
            raise
        except Exception as exc:  # noqa: BLE001
            log.exception("Job %s failed", job.id)
            job.advance(JobStage.FAILED, error=str(exc))
            await self.store.save(job)
            raise

        await self.store.save(job)
        return job

    async def _run_validation(self, job: PrintJob) -> None:
        if job.stage != JobStage.VALIDATING:
            job.advance(JobStage.VALIDATING)
        report = await self.validation_stage.run(job, self.settings)
        job.artifacts.validation = report
        await self.store.save(job)

        if not report.passed:
            raise ValidationFailedError(
                "Model validation failed",
                suggestion=report.to_summary(),
            )

        job.advance(JobStage.AWAITING_VALIDATION_APPROVAL)
        await self.store.save(job)

    async def _run_generation(self, job: PrintJob) -> None:
        await self.generation_stage.run(job, self.settings)
        await self.store.save(job)

    async def _run_slice(self, job: PrintJob) -> None:
        await self.slice_stage.run(job, self.settings)
        await self.store.save(job)

    async def _run_print(self, job: PrintJob) -> None:
        await self.print_stage.run(job, self.settings)

    async def _needs_approval(self, job: PrintJob) -> bool:
        if job.auto_approve:
            next_stage = self._stage_after_approval(job.stage)
            job.advance(next_stage)
            await self.store.save(job)
            return False

        if self.request_approval is None:
            return True

        summary = self._approval_summary(job)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._approval_waiters[job.id] = future
        approved = await self.request_approval(job, summary)
        if not approved:
            job.advance(JobStage.CANCELLED)
            await self.store.save(job)
            return True

        next_stage = self._stage_after_approval(job.stage)
        job.advance(next_stage)
        await self.store.save(job)
        return False

    def _stage_after_approval(self, stage: JobStage) -> JobStage:
        mapping = {
            JobStage.AWAITING_MODEL_APPROVAL: JobStage.VALIDATING,
            JobStage.AWAITING_VALIDATION_APPROVAL: JobStage.SLICING,
            JobStage.AWAITING_SLICE_APPROVAL: JobStage.UPLOADING,
        }
        if stage not in mapping:
            raise JobError(f"Stage {stage.value} does not have an approval gate")
        return mapping[stage]

    def _approval_summary(self, job: PrintJob) -> str:
        if job.stage == JobStage.AWAITING_VALIDATION_APPROVAL:
            report = job.artifacts.validation
            body = report.to_summary() if report else "Validation complete"
            return f"Validation for job {job.id}:\n{body}"
        if job.stage == JobStage.AWAITING_SLICE_APPROVAL:
            filament = job.artifacts.estimated_filament_g
            filament_text = f"{filament:.1f}g" if filament is not None else "unknown"
            return (
                f"Slice complete for job {job.id}\n"
                f"Time: {job.artifacts.estimated_print_time or 'unknown'}\n"
                f"Filament: {filament_text}"
            )
        return f"Approve job {job.id}"

    async def _require_job(self, job_id: str) -> PrintJob:
        job = await self.store.get(job_id)
        if job is None:
            raise JobError(f"Unknown job: {job_id}")
        return job
