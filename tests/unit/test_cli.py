from __future__ import annotations

import asyncio

from bambu_pipe.cli.main import app
from bambu_pipe.models.job import PrintJob
from bambu_pipe.storage.sqlite import SQLiteJobStore
from typer.testing import CliRunner


def test_serve_refuses_unsafe_bind_without_token(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("BAMBU_PIPE_API_TOKEN", raising=False)
    runner = CliRunner()

    result = runner.invoke(app, ["serve", "--host", "0.0.0.0"])

    assert result.exit_code == 2
    assert "BAMBU_PIPE_API_TOKEN" in result.output


def test_jobs_command_reads_configured_sqlite_store(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    database_path = tmp_path / "jobs.db"
    monkeypatch.setenv("BAMBU_PIPE_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("BAMBU_PIPE_STAGING_DIR", str(tmp_path / "staging"))

    job = PrintJob(mode="text_full", prompt="small cube")
    job.artifacts.model_path = str(tmp_path / "model.stl")
    asyncio.run(SQLiteJobStore(database_path).save(job))

    result = CliRunner().invoke(app, ["jobs"])

    assert result.exit_code == 0
    assert job.id in result.output
    assert "pending" in result.output

    show = CliRunner().invoke(app, ["jobs", "show", job.id])
    assert show.exit_code == 0
    assert job.id in show.output

    artifacts = CliRunner().invoke(app, ["jobs", "artifacts", job.id, "--json"])
    assert artifacts.exit_code == 0
    assert "model_path" in artifacts.output
