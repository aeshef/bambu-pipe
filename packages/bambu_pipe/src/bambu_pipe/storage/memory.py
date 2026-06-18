"""In-memory job store for development and tests."""

from __future__ import annotations

from bambu_pipe.models.job import PrintJob


class MemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, PrintJob] = {}

    async def save(self, job: PrintJob) -> None:
        self._jobs[job.id] = job

    async def get(self, job_id: str) -> PrintJob | None:
        return self._jobs.get(job_id)

    async def list(self) -> list[PrintJob]:
        return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
