"""Public Python API for bambu-pipe."""

from __future__ import annotations

from pathlib import Path

from bambu_pipe.config import Settings, load_settings
from bambu_pipe.models.job import JobStage, PipelineMode, PrintJob
from bambu_pipe.models.validation import ValidationReport
from bambu_pipe.orchestrator import PipelineOrchestrator


class BambuPipeline:
    """Small public facade for local-first print automation.

    Use this class from scripts, notebooks, or local adapters instead
    of importing orchestration internals directly.

    Methods named `validate_*` and `slice_*` never upload files or start the
    printer. Methods named `print_*` may upload and start a print after the
    configured approval gates are satisfied.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        orchestrator: PipelineOrchestrator | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.orchestrator = orchestrator or PipelineOrchestrator(self.settings)

    @classmethod
    def from_env(cls) -> BambuPipeline:
        """Create a pipeline from `BAMBU_PIPE_*` environment/config settings."""
        return cls(load_settings())

    async def create_job(
        self,
        *,
        mode: PipelineMode,
        prompt: str = "",
        model_path: str | Path | None = None,
        quality: str | None = None,
        material: str | None = None,
        auto_approve: bool | None = None,
    ) -> PrintJob:
        """Create a persisted job without running pipeline stages.

        Use this when an adapter wants to create a job first and drive execution
        or approval separately.
        """
        return await self.orchestrator.create_job(
            mode=mode,
            prompt=prompt,
            model_path=str(model_path) if model_path is not None else None,
            quality=quality,
            material=material,
            auto_approve=auto_approve,
        )

    async def run_job(self, job_id: str) -> PrintJob:
        """Resume a job through the configured pipeline.

        Depending on job mode and approval policy, this may validate, generate,
        slice, upload, and start a print.
        """
        return await self.orchestrator.run_mesh_pipeline(job_id)

    async def validate_model(
        self,
        model_path: str | Path,
        *,
        quality: str | None = None,
        material: str | None = None,
    ) -> ValidationReport:
        """Validate a model and return a `ValidationReport`.

        This is a dry-run helper: it never slices, uploads, or starts a print.
        """
        job = await self.create_job(
            mode="mesh_only",
            model_path=model_path,
            quality=quality,
            material=material,
            auto_approve=False,
        )
        job.advance(JobStage.VALIDATING)
        report = await self.orchestrator.validation_stage.run(job, self.settings)
        job.artifacts.validation = report
        if report.passed:
            job.advance(JobStage.AWAITING_VALIDATION_APPROVAL)
        else:
            job.advance(JobStage.FAILED, error=report.to_summary())
        await self.orchestrator.store.save(job)
        return report

    async def slice_model(
        self,
        model_path: str | Path,
        *,
        quality: str | None = None,
        material: str | None = None,
    ) -> PrintJob:
        """Validate and slice a model locally.

        This is a dry-run helper: it writes local slice artifacts but never
        uploads to the printer and never starts a print.
        """
        job = await self.create_job(
            mode="mesh_only",
            model_path=model_path,
            quality=quality,
            material=material,
            auto_approve=False,
        )
        job.advance(JobStage.VALIDATING)
        report = await self.orchestrator.validation_stage.run(job, self.settings)
        job.artifacts.validation = report
        if not report.passed:
            job.advance(JobStage.FAILED, error=report.to_summary())
            await self.orchestrator.store.save(job)
            return job
        job.advance(JobStage.AWAITING_VALIDATION_APPROVAL)
        job.advance(JobStage.SLICING)
        await self.orchestrator.slice_stage.run(job, self.settings)
        await self.orchestrator.store.save(job)
        return job

    async def plan_print(
        self,
        *,
        prompt: str = "",
        model_path: str | Path | None = None,
        quality: str | None = None,
        material: str | None = None,
    ) -> PrintJob:
        """Prepare a full local print plan without uploading or starting the printer.

        For `model_path`, this validates and slices the model. For `prompt`, this
        also runs the configured mesh provider first. The returned job stops at
        `awaiting_slice_approval` when planning succeeds.
        """
        mode: PipelineMode = "mesh_only" if model_path is not None else "text_full"
        job = await self.create_job(
            mode=mode,
            prompt=prompt,
            model_path=model_path,
            quality=quality,
            material=material,
            auto_approve=False,
        )
        if mode == "text_full":
            job.advance(JobStage.GENERATING)
            await self.orchestrator.generation_stage.run(job, self.settings)
            await self.orchestrator.store.save(job)
            job.advance(JobStage.VALIDATING)
        else:
            job.advance(JobStage.VALIDATING)

        report = await self.orchestrator.validation_stage.run(job, self.settings)
        job.artifacts.validation = report
        if not report.passed:
            job.advance(JobStage.FAILED, error=report.to_summary())
            await self.orchestrator.store.save(job)
            return job

        job.advance(JobStage.AWAITING_VALIDATION_APPROVAL)
        job.advance(JobStage.SLICING)
        await self.orchestrator.slice_stage.run(job, self.settings)
        await self.orchestrator.store.save(job)
        return job

    async def print_model(
        self,
        model_path: str | Path,
        *,
        quality: str | None = None,
        material: str | None = None,
        auto_approve: bool | None = None,
    ) -> PrintJob:
        """Run the mesh-only pipeline for an existing model.

        This method can upload to the printer and start a print after approval
        gates pass.
        """
        job = await self.create_job(
            mode="mesh_only",
            model_path=model_path,
            quality=quality,
            material=material,
            auto_approve=auto_approve,
        )
        return await self.run_job(job.id)

    async def print_prompt(
        self,
        prompt: str,
        *,
        quality: str | None = None,
        material: str | None = None,
        auto_approve: bool | None = None,
    ) -> PrintJob:
        """Generate a mesh from text and run the full print pipeline.

        This method requires a configured mesh provider and can upload to the
        printer and start a print after approval gates pass.
        """
        job = await self.create_job(
            mode="text_full",
            prompt=prompt,
            quality=quality,
            material=material,
            auto_approve=auto_approve,
        )
        return await self.run_job(job.id)
