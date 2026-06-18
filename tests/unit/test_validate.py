from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bambu_pipe.config import Settings
from bambu_pipe.models.errors import SliceError
from bambu_pipe.models.job import JobStage, PrintJob
from bambu_pipe.models.validation import ValidationCheck, ValidationReport
from bambu_pipe.orchestrator import PipelineOrchestrator
from bambu_pipe.stages.slice import DefaultSliceStage, _estimated_minutes
from bambu_pipe.stages.validate import DefaultValidationStage


@pytest.mark.asyncio
async def test_validation_passes_for_small_cube(tmp_settings: Settings) -> None:
    cube = Path(__file__).resolve().parents[1] / "fixtures" / "cube.stl"
    job = PrintJob(model_path=str(cube))
    job.artifacts.model_path = str(cube)
    report = await DefaultValidationStage().run(job, tmp_settings)
    assert report.passed
    assert report.score == 100
    assert any(check.name == "bed_fit" and check.passed for check in report.checks)
    assert any(check.name == "file_size" and check.passed for check in report.checks)


def test_validation_report_score_field() -> None:
    report = ValidationReport(
        checks=[ValidationCheck(name="watertight", passed=True, message="ok")],
        score=87,
    )
    assert report.passed
    assert report.score == 87


@pytest.mark.asyncio
async def test_mesh_pipeline_stops_at_validation_gate(
    tmp_settings: Settings,
) -> None:
    cube = Path(__file__).resolve().parents[1] / "fixtures" / "cube.stl"
    orchestrator = PipelineOrchestrator(tmp_settings)

    slice_mock = AsyncMock()
    orchestrator.slice_stage.run = slice_mock

    job = await orchestrator.create_job(model_path=str(cube))
    result = await orchestrator.run_mesh_pipeline(job.id)

    assert result.stage == JobStage.AWAITING_VALIDATION_APPROVAL
    slice_mock.assert_not_called()


@pytest.mark.asyncio
async def test_mesh_pipeline_full_with_mocks(tmp_settings: Settings) -> None:
    cube = Path(__file__).resolve().parents[1] / "fixtures" / "cube.stl"
    tmp_settings.auto_approve = True
    orchestrator = PipelineOrchestrator(tmp_settings)

    slice_result_path = tmp_settings.staging_dir / "slice.gcode.3mf"

    async def fake_slice(job: PrintJob, settings: Settings) -> None:
        if job.stage != JobStage.SLICING:
            job.advance(JobStage.SLICING)
        slice_result_path.parent.mkdir(parents=True, exist_ok=True)
        slice_result_path.write_bytes(b"fake")
        job.artifacts.sliced_path = str(slice_result_path)
        job.artifacts.estimated_print_time = "10m"
        job.artifacts.estimated_filament_g = 5.0
        job.advance(JobStage.AWAITING_SLICE_APPROVAL)

    async def fake_print(job: PrintJob, settings: Settings) -> None:
        if job.stage != JobStage.UPLOADING:
            job.advance(JobStage.UPLOADING)
        job.advance(JobStage.PRINTING)
        job.advance(JobStage.DONE)

    orchestrator.slice_stage.run = fake_slice
    orchestrator.print_stage.run = fake_print

    job = await orchestrator.create_job(model_path=str(cube))
    result = await orchestrator.run_mesh_pipeline(job.id)
    assert result.stage == JobStage.DONE


@pytest.mark.asyncio
async def test_slice_stage_uses_job_quality_and_material(tmp_settings: Settings) -> None:
    captured: dict[str, str] = {}
    cube = Path(__file__).resolve().parents[1] / "fixtures" / "cube.stl"
    job = PrintJob(model_path=str(cube), quality="fine", material="PETG")
    job.artifacts.model_path = str(cube)
    job.advance(JobStage.SLICING)

    class FakeSlicer:
        async def slice(self, model_path, output_path, settings):  # noqa: ANN001
            from bambu_pipe.providers.slicer.base import SliceResult

            captured["quality"] = settings.quality
            captured["material"] = settings.material
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake")
            return SliceResult(output_path=output_path)

    await DefaultSliceStage(slicer=FakeSlicer()).run(job, tmp_settings)  # type: ignore[arg-type]

    assert captured == {"quality": "fine", "material": "PETG"}


def test_estimated_minutes_parses_orca_time_strings() -> None:
    assert _estimated_minutes("19h 25m 8s") == pytest.approx(1165.133, rel=0.001)
    assert _estimated_minutes("10m") == pytest.approx(10)
    assert _estimated_minutes("01:30:00") == pytest.approx(90)


@pytest.mark.asyncio
async def test_slice_stage_rejects_overlong_estimate(tmp_settings: Settings) -> None:
    from bambu_pipe.providers.slicer.base import SliceResult

    tmp_settings.max_estimated_print_minutes = 240
    cube = Path(__file__).resolve().parents[1] / "fixtures" / "cube.stl"
    job = PrintJob(model_path=str(cube))
    job.artifacts.model_path = str(cube)
    job.advance(JobStage.SLICING)

    class FakeSlicer:
        async def slice(self, model_path, output_path, settings):  # noqa: ANN001
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake")
            return SliceResult(output_path=output_path, estimated_print_time="19h 25m 8s")

    with pytest.raises(SliceError) as exc_info:
        await DefaultSliceStage(slicer=FakeSlicer()).run(job, tmp_settings)  # type: ignore[arg-type]

    assert "Estimated print time is too long" in str(exc_info.value)


@pytest.mark.asyncio
async def test_slice_stage_allows_overlong_estimate_without_configured_limit(
    tmp_settings: Settings,
    tmp_path: Path,
) -> None:
    from bambu_pipe.providers.slicer.base import SliceResult

    tmp_settings.max_estimated_print_minutes = None
    cube = tmp_path / "cube.stl"
    cube.write_text("solid cube\nendsolid cube\n", encoding="utf-8")
    job = PrintJob(model_path=str(cube))
    job.artifacts.model_path = str(cube)
    job.advance(JobStage.SLICING)

    class FakeSlicer:
        async def slice(self, model_path, output_path, settings):  # noqa: ANN001
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"fake")
            return SliceResult(output_path=output_path, estimated_print_time="19h 25m 8s")

    await DefaultSliceStage(slicer=FakeSlicer()).run(job, tmp_settings)  # type: ignore[arg-type]

    assert job.stage == JobStage.AWAITING_SLICE_APPROVAL
