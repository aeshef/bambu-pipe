from __future__ import annotations

import pytest
from bambu_pipe.models.job import JobStage, PrintJob
from bambu_pipe.storage.sqlite import SQLiteJobStore


@pytest.mark.asyncio
async def test_sqlite_job_store_persists_jobs(tmp_path) -> None:
    store = SQLiteJobStore(tmp_path / "jobs.db")
    job = PrintJob(prompt="test", material="TPU")
    job.advance(JobStage.VALIDATING)
    await store.save(job)

    reloaded_store = SQLiteJobStore(tmp_path / "jobs.db")
    loaded = await reloaded_store.get(job.id)

    assert loaded is not None
    assert loaded.id == job.id
    assert loaded.material == "TPU"
    assert loaded.stage == JobStage.VALIDATING
    assert [row.id for row in await reloaded_store.list()] == [job.id]
