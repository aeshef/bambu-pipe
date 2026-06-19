# Python API

`bambu_pipe.BambuPipeline` is the public library facade. Use it from scripts,
local adapters, notebooks, or home automation code instead of importing
orchestration internals.

## Install

```bash
pip install "bambu-pipe"
pip install "bambu-pipe[tripo]"  # needed for text_full / print_prompt
```

## Validate Without Printing

```python
import asyncio

from bambu_pipe import BambuPipeline


async def main() -> None:
    pipeline = BambuPipeline.from_env()
    report = await pipeline.validate_model("model.stl", material="PETG")
    print(report.score, report.passed)


asyncio.run(main())
```

Guarantee: `validate_model()` never slices, uploads, or starts a print.

## Slice Without Printing

```python
import asyncio

from bambu_pipe import BambuPipeline


async def main() -> None:
    pipeline = BambuPipeline.from_env()
    job = await pipeline.slice_model("model.stl", material="PETG")
    print(job.artifacts.sliced_path)
    print(job.artifacts.thumbnail_path)


asyncio.run(main())
```

Guarantee: `slice_model()` writes local slice artifacts, but never uploads or
starts a print.

## Plan A Print Without Printing

```python
import asyncio

from bambu_pipe import BambuPipeline


async def main() -> None:
    pipeline = BambuPipeline.from_env()
    job = await pipeline.plan_print(
        prompt="small low-poly cat figurine, printable as one object",
        material="PLA",
    )
    print(job.artifacts.preview_html_path)
    print(job.artifacts.artifact_manifest_path)


asyncio.run(main())
```

Guarantee: `plan_print()` may generate and slice local artifacts, but never
uploads to the printer and never starts a print.

## Print An Existing Model

```python
import asyncio

from bambu_pipe import BambuPipeline


async def main() -> None:
    pipeline = BambuPipeline.from_env()
    job = await pipeline.print_model("model.stl", material="PETG", auto_approve=False)
    print(job.id, job.stage)


asyncio.run(main())
```

`print_model()` may upload to the printer and start a print after approval gates
are satisfied.

## Print From A Prompt

```python
import asyncio

from bambu_pipe import BambuPipeline


async def main() -> None:
    pipeline = BambuPipeline.from_env()
    job = await pipeline.print_prompt(
        "small low-poly cat figurine, printable as one object",
        material="PLA",
        auto_approve=False,
    )
    print(job.id, job.stage)


asyncio.run(main())
```

`print_prompt()` requires a configured mesh provider and may upload/start a print
after approval gates are satisfied.
