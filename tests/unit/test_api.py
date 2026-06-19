from __future__ import annotations

from pathlib import Path

import pytest
from bambu_pipe.config import Settings
from httpx import ASGITransport, AsyncClient

from apps.api.main import create_app


def configure_test_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    monkeypatch.setenv("BAMBU_PIPE_STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("BAMBU_PIPE_DATABASE_PATH", str(tmp_path / "jobs.db"))
    monkeypatch.setenv(
        "BAMBU_PIPE_PROFILES_DIR",
        str(Path(__file__).resolve().parents[1] / "fixtures" / "profiles"),
    )

    app = create_app()
    from bambu_pipe.orchestrator import PipelineOrchestrator

    app.state.settings = Settings()
    app.state.orchestrator = PipelineOrchestrator(app.state.settings)
    return app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_and_run_job_with_mocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = configure_test_app(tmp_path, monkeypatch)
    orchestrator = app.state.orchestrator

    async def fake_slice(job, settings):  # noqa: ANN001
        from bambu_pipe.models.job import JobStage

        if job.stage != JobStage.SLICING:
            job.advance(JobStage.SLICING)
        output = tmp_path / "staging" / job.id / "out.gcode.3mf"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fake")
        job.artifacts.sliced_path = str(output)
        job.advance(JobStage.AWAITING_SLICE_APPROVAL)

    async def fake_print(job, settings):  # noqa: ANN001
        from bambu_pipe.models.job import JobStage

        if job.stage != JobStage.UPLOADING:
            job.advance(JobStage.UPLOADING)
        job.advance(JobStage.PRINTING)
        job.advance(JobStage.DONE)

    orchestrator.slice_stage.run = fake_slice
    orchestrator.print_stage.run = fake_print

    cube = Path(__file__).resolve().parents[1] / "fixtures" / "cube.stl"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post(
            "/api/v1/jobs/upload",
            files={"file": ("cube.stl", cube.read_bytes(), "model/stl")},
            params={"auto_approve": True},
        )
        assert create.status_code == 200
        assert create.json()["auto_approve"] is True
        assert app.state.settings.auto_approve is False
        job_id = create.json()["id"]
        run = await client.post(f"/api/v1/jobs/{job_id}/run")
        assert run.status_code == 200
        assert run.json()["stage"] == "done"
        preview = await client.get(f"/api/v1/jobs/{job_id}/preview")
        assert preview.status_code == 200
        assert preview.json()["confidence_score"] == 100
        assert preview.json()["has_slice"] is True


@pytest.mark.asyncio
async def test_print_upload_shortcut_runs_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = configure_test_app(tmp_path, monkeypatch)
    orchestrator = app.state.orchestrator

    async def fake_slice(job, settings):  # noqa: ANN001
        from bambu_pipe.models.job import JobStage

        if job.stage != JobStage.SLICING:
            job.advance(JobStage.SLICING)
        output = tmp_path / "shortcut.gcode.3mf"
        output.write_bytes(b"fake")
        job.artifacts.sliced_path = str(output)
        job.advance(JobStage.AWAITING_SLICE_APPROVAL)

    async def fake_print(job, settings):  # noqa: ANN001
        from bambu_pipe.models.job import JobStage

        job.advance(JobStage.PRINTING)
        job.advance(JobStage.DONE)

    orchestrator.slice_stage.run = fake_slice
    orchestrator.print_stage.run = fake_print

    cube = Path(__file__).resolve().parents[1] / "fixtures" / "cube.stl"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs/print",
            files={"file": ("cube.stl", cube.read_bytes(), "model/stl")},
            params={"auto_approve": True},
        )

    assert response.status_code == 200
    assert response.json()["stage"] == "done"


@pytest.mark.asyncio
async def test_text_full_job_runs_generation_with_mock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = configure_test_app(tmp_path, monkeypatch)
    orchestrator = app.state.orchestrator

    async def fake_validation(job, settings):  # noqa: ANN001
        from bambu_pipe.models.validation import ValidationReport

        return ValidationReport(checks=[])

    async def fake_generate(job, settings):  # noqa: ANN001
        from bambu_pipe.models.job import JobStage

        generated = tmp_path / "generated.stl"
        generated.write_text("solid generated\nendsolid generated\n")
        job.artifacts.model_path = str(generated)
        job.model_path = str(generated)
        job.advance(JobStage.AWAITING_MODEL_APPROVAL)

    async def fake_slice(job, settings):  # noqa: ANN001
        from bambu_pipe.models.job import JobStage

        if job.stage != JobStage.SLICING:
            job.advance(JobStage.SLICING)
        output = tmp_path / "generated.gcode.3mf"
        output.write_bytes(b"fake")
        job.artifacts.sliced_path = str(output)
        job.advance(JobStage.AWAITING_SLICE_APPROVAL)

    async def fake_print(job, settings):  # noqa: ANN001
        from bambu_pipe.models.job import JobStage

        job.advance(JobStage.PRINTING)
        job.advance(JobStage.DONE)

    orchestrator.generation_stage.run = fake_generate
    orchestrator.validation_stage.run = fake_validation
    orchestrator.slice_stage.run = fake_slice
    orchestrator.print_stage.run = fake_print

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create = await client.post(
            "/api/v1/jobs",
            json={"mode": "text_full", "prompt": "small calibration cube", "auto_approve": True},
        )
        assert create.status_code == 200
        run = await client.post(f"/api/v1/jobs/{create.json()['id']}/run")

    assert run.status_code == 200
    assert run.json()["stage"] == "done"


@pytest.mark.asyncio
async def test_upload_job_endpoint_creates_job_with_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = configure_test_app(tmp_path, monkeypatch)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs/upload",
            files={"file": ("cube.stl", b"solid cube\nendsolid cube\n", "model/stl")},
            params={"material": "PETG", "quality": "fine"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "pending"
    assert body["artifacts"]["model_path"].endswith("upload.stl")


@pytest.mark.asyncio
async def test_jobs_endpoint_rejects_local_model_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = configure_test_app(tmp_path, monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs",
            json={"mode": "mesh_only", "model_path": "/etc/passwd"},
        )

    assert response.status_code == 400
    assert "model_path is disabled" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_job_endpoint_enforces_size_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BAMBU_PIPE_MAX_UPLOAD_MB", "1")

    app = configure_test_app(tmp_path, monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs/upload",
            files={"file": ("too-large.stl", b"0" * (1024 * 1024 + 1), "model/stl")},
        )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_mutating_api_requires_token_when_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = configure_test_app(tmp_path, monkeypatch)
    app.state.settings = Settings(api_token="test-token")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs",
            json={"mode": "text_full", "prompt": "small cube"},
        )

    assert response.status_code == 401
    assert "BAMBU_PIPE_API_TOKEN" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mutating_api_accepts_bearer_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = configure_test_app(tmp_path, monkeypatch)
    app.state.settings = Settings(api_token="test-token")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs",
            headers={"Authorization": "Bearer test-token"},
            json={"mode": "text_full", "prompt": "small cube"},
        )

    assert response.status_code == 200
    assert response.json()["mode"] == "text_full"
