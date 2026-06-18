"""Stage protocols."""

from __future__ import annotations

from typing import Protocol

from bambu_pipe.config import Settings
from bambu_pipe.models.job import PrintJob
from bambu_pipe.models.validation import ValidationReport


class ValidationStage(Protocol):
    async def run(self, job: PrintJob, settings: Settings) -> ValidationReport: ...


class SliceStage(Protocol):
    async def run(self, job: PrintJob, settings: Settings) -> None: ...


class GenerationStage(Protocol):
    async def run(self, job: PrintJob, settings: Settings) -> None: ...


class PrintStage(Protocol):
    async def run(self, job: PrintJob, settings: Settings) -> None: ...
