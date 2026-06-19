"""Slice stage."""

from __future__ import annotations

import re
from pathlib import Path

from bambu_pipe.artifacts import write_preview_artifacts
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
        _enforce_print_time_limit(job, settings)
        job.advance(JobStage.AWAITING_SLICE_APPROVAL)
        write_preview_artifacts(job, job_staging_dir(settings.staging_dir, job.id))


def _enforce_print_time_limit(job: PrintJob, settings: Settings) -> None:
    limit = settings.max_estimated_print_minutes
    if limit is None:
        return
    estimated = _estimated_minutes(job.artifacts.estimated_print_time)
    if estimated is None or estimated <= limit:
        return
    raise SliceError(
        f"Estimated print time is too long: {job.artifacts.estimated_print_time}",
        suggestion=(
            f"Current safety limit is {limit} minutes. Use a smaller model, lower detail, "
            "or raise BAMBU_PIPE_MAX_ESTIMATED_PRINT_MINUTES intentionally."
        ),
    )


def _estimated_minutes(value: str | None) -> float | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None

    total = 0.0
    matched = False
    for amount, unit in re.findall(r"(\d+(?:\.\d+)?)\s*([dhms])", normalized):
        matched = True
        number = float(amount)
        if unit == "d":
            total += number * 24 * 60
        elif unit == "h":
            total += number * 60
        elif unit == "m":
            total += number
        elif unit == "s":
            total += number / 60
    if matched:
        return total

    clock_match = re.fullmatch(r"(?:(\d+):)?(\d+):(\d+)", normalized)
    if clock_match:
        hours = int(clock_match.group(1) or 0)
        minutes = int(clock_match.group(2))
        seconds = int(clock_match.group(3))
        return hours * 60 + minutes + seconds / 60

    return None
