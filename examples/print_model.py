"""Print an existing mesh through the public Python API."""

from __future__ import annotations

import asyncio
from pathlib import Path

from bambu_pipe import BambuPipeline


async def main() -> None:
    pipeline = BambuPipeline.from_env()
    job = await pipeline.print_model(
        Path("model.stl"),
        material="PETG",
        auto_approve=False,
    )
    print(f"Created job {job.id} in stage {job.stage.value}")


if __name__ == "__main__":
    asyncio.run(main())
