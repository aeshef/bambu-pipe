"""Small deterministic tools for the agent's design/review loop."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import typer

from bambu_pipe.design.workspace import (
    build_design,
    init_design,
    install_skill,
    review_design,
    verify_design,
)

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Local parametric CAD builds and revision-bound visual review",
)


def _emit(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2, allow_nan=False))


def _fail(exc: Exception) -> None:
    typer.echo(f"Design failed: {exc}", err=True)
    raise typer.Exit(code=2) from exc


@app.command("doctor")
def doctor() -> None:
    """Check CAD dependencies without configuring a printer or contacting a provider."""
    checks = {
        name: importlib.util.find_spec(name) is not None
        for name in ("cadquery", "matplotlib", "trimesh")
    }
    _emit(
        {
            "python": sys.version.split()[0],
            "dependencies": checks,
            "suggestion": 'Use Python 3.11 or 3.12 and pip install "bambu-pipe[cad]"',
        }
    )
    if not all(checks.values()):
        raise typer.Exit(code=2)


@app.command("init")
def init(
    workspace: Path,
    brief: str = typer.Option("80 × 40 × 4 mm mounting plate, two 5 mm holes", "--brief"),
) -> None:
    """Create a starter CAD source and independent acceptance spec in an empty folder."""
    try:
        path = init_design(workspace, brief)
        _emit(
            {
                "workspace": str(path),
                "next": "Adapt model.py and spec.json to the brief, then build",
            }
        )
    except (ValueError, OSError) as exc:
        _fail(exc)


@app.command("build")
def build(
    workspace: Path,
    timeout: int = typer.Option(300, "--timeout", min=1),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run CAD, export STEP/STL, check geometry, render four PNGs; never contact the printer."""
    try:
        report = build_design(workspace, timeout)
    except (ValueError, OSError, KeyError, ImportError) as exc:
        _fail(exc)
    if json_output:
        _emit(report)
    else:
        typer.echo(f"Build: {report['build_id']}")
        for check in report["checks"]:
            typer.echo(
                f"{'PASS' if check['passed'] else 'FAIL'} {check['name']}: {check['message']}"
            )
        typer.echo(f"Inspect: {Path(report['output_dir']) / 'preview.html'}")
        typer.echo("Visual review and slicer inspection are still required.")
    if not report["passed"]:
        raise typer.Exit(code=2)


@app.command("review")
def review(
    workspace: Path,
    decision: str = typer.Option(..., "--decision", help="accept or revise"),
    reviewer: str = typer.Option(..., "--reviewer"),
    notes: str = typer.Option(..., "--notes"),
    viewed: list[str] = typer.Option([], "--view", help="Each inspected PNG filename"),
) -> None:
    """Record a visual reviewer attestation bound to the current source, spec and artifacts."""
    try:
        _emit(
            review_design(
                workspace, decision=decision, reviewer=reviewer, notes=notes, viewed=viewed
            )
        )
    except (ValueError, OSError, KeyError) as exc:
        _fail(exc)


@app.command("verify")
def verify(workspace: Path) -> None:
    """Reject missing reviews, changed inputs, modified exports or failed mechanical checks."""
    try:
        _emit(verify_design(workspace))
    except (ValueError, OSError, KeyError) as exc:
        _fail(exc)


@app.command("slice")
def slice_design(
    workspace: Path,
    material: str = typer.Option("PLA", "--material"),
    quality: str = typer.Option("standard", "--quality"),
) -> None:
    """Verify reviewed CAD, then validate and slice locally for inspection; never print."""
    from bambu_pipe.models.errors import BambuPipeError
    from bambu_pipe.models.job import JobStage
    from bambu_pipe.pipeline import BambuPipeline

    async def run() -> None:
        design = verify_design(workspace)
        job = await BambuPipeline.from_env().slice_model(
            design["model_path"], quality=quality, material=material.upper()
        )
        _emit(job.model_dump(mode="json"))
        if job.stage == JobStage.FAILED:
            raise typer.Exit(code=2)

    try:
        asyncio.run(run())
    except (ValueError, OSError, KeyError, BambuPipeError) as exc:
        _fail(exc)


@app.command("install-skill")
def skill(target: Path = typer.Option(..., "--target", help="Parent skills folder")) -> None:
    """Copy the bundled agent skill to an explicit skills folder without overwriting."""
    try:
        _emit({"skill_path": str(install_skill(target))})
    except (ValueError, OSError) as exc:
        _fail(exc)
