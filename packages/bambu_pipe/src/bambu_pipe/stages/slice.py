"""Slice stage."""

from __future__ import annotations

from pathlib import Path

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import SliceError
from bambu_pipe.models.job import JobStage, PrintJob
from bambu_pipe.paths import job_staging_dir
from bambu_pipe.providers.slicer.local_orca import LocalOrcaSlicer


class DefaultSliceStage:
    def __init__(self, slicer: LocalOrcaSlicer | None = None) -> None:
        self._slicer = slicer or LocalOrcaSlicer()

    async def run(self, job: PrintJob, settings: Settings) -> None:
        model_path = job.artifacts.model_path or job.model_path
        if not model_path:
            raise SliceError("No model available for slicing")

        source = Path(model_path)
        if not source.is_file():
            raise SliceError(f"Model file not found: {source}")

        if job.stage != JobStage.SLICING:
            job.advance(JobStage.SLICING)
        staging = job_staging_dir(settings.staging_dir, job.id)
        output_path = staging / f"{source.stem}.gcode.3mf"

        effective_settings = settings.model_copy(
            update={"quality": job.quality, "material": job.material.upper()}
        )
        result = await self._slicer.slice(source, output_path, effective_settings)
        job.artifacts.sliced_path = str(result.output_path)
        job.artifacts.thumbnail_path = str(result.thumbnail_path) if result.thumbnail_path else None
        job.artifacts.estimated_print_time = result.estimated_print_time
        job.artifacts.estimated_filament_g = result.estimated_filament_g
        job.advance(JobStage.AWAITING_SLICE_APPROVAL)
