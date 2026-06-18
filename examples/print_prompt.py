"""Generate a mesh from text, then run it through the print pipeline."""

from __future__ import annotations

import asyncio

from bambu_pipe import BambuPipeline


async def main() -> None:
    pipeline = BambuPipeline.from_env()
    job = await pipeline.print_prompt(
        "small low-poly cat figurine, printable as one object",
        material="PLA",
        auto_approve=False,
    )
    print(f"Created job {job.id} in stage {job.stage.value}")


if __name__ == "__main__":
    asyncio.run(main())
