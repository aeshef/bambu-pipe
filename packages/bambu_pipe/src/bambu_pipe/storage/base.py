"""Job persistence protocol."""

from __future__ import annotations

from typing import Protocol

from bambu_pipe.models.job import PrintJob


class JobStore(Protocol):
    async def save(self, job: PrintJob) -> None: ...

    async def get(self, job_id: str) -> PrintJob | None: ...

    async def list(self) -> list[PrintJob]: ...
