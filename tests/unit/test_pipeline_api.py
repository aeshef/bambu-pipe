from __future__ import annotations

from pathlib import Path

import pytest
from bambu_pipe import BambuPipeline
from bambu_pipe.config import Settings
from bambu_pipe.models.job import JobStage
from bambu_pipe.models.validation import ValidationReport


@pytest.mark.asyncio
async def test_public_pipeline_print_model_runs_job(tmp_path: Path) -> None:
    settings = Settings(
        staging_dir=tmp_path / "staging",
        database_path=tmp_path / "jobs.db",
        profiles_dir=Path(__file__).resolve().parents[1] / "fixtures" / "profiles",
    )
    pipeline = BambuPipeline(settings)

    async def validate(job, settings):  # noqa: ANN001
        return ValidationReport(checks=[])

    async def slice_job(job, settings):  # noqa: ANN001
        if job.stage != JobStage.SLICING:
            job.advance(JobStage.SLICING)
        output = tmp_path / "model.gcode.3mf"
        output.write_bytes(b"slice")
        job.artifacts.sliced_path = str(output)
        job.advance(JobStage.AWAITING_SLICE_APPROVAL)

    async def print_job(job, settings):  # noqa: ANN001
        job.advance(JobStage.PRINTING)
        job.advance(JobStage.DONE)

    pipeline.orchestrator.validation_stage.run = validate
    pipeline.orchestrator.slice_stage.run = slice_job
    pipeline.orchestrator.print_stage.run = print_job

    model = tmp_path / "model.stl"
    model.write_text("solid model\nendsolid model\n", encoding="utf-8")

    job = await pipeline.print_model(model, auto_approve=True)

    assert job.stage == JobStage.DONE
    assert job.artifacts.sliced_path is not None


@pytest.mark.asyncio
async def test_public_pipeline_validate_model_returns_report(tmp_path: Path) -> None:
    settings = Settings(
        staging_dir=tmp_path / "staging",
        database_path=tmp_path / "jobs.db",
        profiles_dir=Path(__file__).resolve().parents[1] / "fixtures" / "profiles",
    )
    pipeline = BambuPipeline(settings)

    async def validate(job, settings):  # noqa: ANN001
        return ValidationReport(checks=[], score=100)

    pipeline.orchestrator.validation_stage.run = validate
    model = tmp_path / "model.stl"
    model.write_text("solid model\nendsolid model\n", encoding="utf-8")

    report = await pipeline.validate_model(model)

    assert report.passed is True
    assert report.score == 100


@pytest.mark.asyncio
async def test_public_pipeline_slice_model_does_not_print(tmp_path: Path) -> None:
    settings = Settings(
        staging_dir=tmp_path / "staging",
        database_path=tmp_path / "jobs.db",
        profiles_dir=Path(__file__).resolve().parents[1] / "fixtures" / "profiles",
    )
    pipeline = BambuPipeline(settings)

    async def validate(job, settings):  # noqa: ANN001
        return ValidationReport(checks=[], score=100)

    async def slice_job(job, settings):  # noqa: ANN001
        output = tmp_path / "dry-run.gcode.3mf"
        output.write_bytes(b"slice")
        job.artifacts.sliced_path = str(output)
        job.advance(JobStage.AWAITING_SLICE_APPROVAL)

    pipeline.orchestrator.validation_stage.run = validate
    pipeline.orchestrator.slice_stage.run = slice_job
    model = tmp_path / "model.stl"
    model.write_text("solid model\nendsolid model\n", encoding="utf-8")

    job = await pipeline.slice_model(model)

    assert job.stage == JobStage.AWAITING_SLICE_APPROVAL
    assert job.artifacts.sliced_path is not None
    assert job.artifacts.remote_filename is None


def test_public_pipeline_import() -> None:
    assert BambuPipeline.__name__ == "BambuPipeline"
