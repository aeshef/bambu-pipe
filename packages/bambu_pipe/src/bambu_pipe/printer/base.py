"""Printer provider protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from bambu_pipe.config import Settings


class PrinterClient(Protocol):
    async def ensure_reachable(self, settings: Settings) -> None: ...

    async def upload(self, settings: Settings, local_path: Path) -> str: ...

    async def start_print(self, settings: Settings, filename: str) -> None: ...

    async def upload_and_print(self, settings: Settings, local_path: Path) -> str: ...

    async def status(self, settings: Settings) -> dict[str, object]: ...
