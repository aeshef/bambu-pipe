"""Print stage — upload sliced job and start printing."""

from __future__ import annotations

from pathlib import Path

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import PrinterError
from bambu_pipe.models.job import JobStage, PrintJob
from bambu_pipe.printer.base import PrinterClient
from bambu_pipe.printer.client import BambuPrinterClient


class DefaultPrintStage:
    def __init__(self, printer: PrinterClient | None = None) -> None:
        self._printer = printer or BambuPrinterClient()

    async def run(self, job: PrintJob, settings: Settings) -> None:
        sliced = job.artifacts.sliced_path
        if not sliced:
            raise PrinterError("No sliced file available for printing")

        path = Path(sliced)
        if not path.is_file():
            raise PrinterError(f"Sliced file not found: {path}")

        if job.stage != JobStage.UPLOADING:
            job.advance(JobStage.UPLOADING)
        remote_name = await self._printer.upload(settings, path)
        job.artifacts.remote_filename = remote_name

        job.advance(JobStage.PRINTING)
        await self._printer.start_print(settings, remote_name)
        job.advance(JobStage.DONE)
