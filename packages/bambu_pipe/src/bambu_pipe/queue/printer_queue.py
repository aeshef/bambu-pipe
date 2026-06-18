"""Serialize concurrent printer access."""

from __future__ import annotations

import asyncio


class PrinterQueue:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def run(self, coro_factory):  # noqa: ANN001
        async with self._lock:
            return await coro_factory()
