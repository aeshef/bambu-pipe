"""Command-line interface."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from bambu_pipe.config import Settings, load_settings
from bambu_pipe.doctor import run_doctor
from bambu_pipe.models.job import JobStage
from bambu_pipe.models.validation import ValidationReport
from bambu_pipe.orchestrator import PipelineOrchestrator
from bambu_pipe.pipeline import BambuPipeline
from bambu_pipe.printer.client import BambuPrinterClient

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def _settings_ctx(
    auto_approve: bool = typer.Option(False, "--yes", "-y", help="Skip approval gates"),
) -> Settings:
    settings = load_settings()
    if auto_approve:
        settings.auto_approve = True
    return settings


@app.command()
def doctor() -> None:
    """Check local configuration and dependencies."""
    report = run_doctor(load_settings())
    table = Table(title="bambu-pipe doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")
    for check in report.checks:
        table.add_row(
            check.name,
            "ok" if check.ok else "fail",
            check.message if check.ok else f"{check.message}. {check.suggestion or ''}",
        )
    console.print(table)
    raise typer.Exit(code=0 if report.ok else 1)


@app.command()
def status() -> None:
    """Show printer status."""
    settings = load_settings()

    async def _run() -> None:
        client = BambuPrinterClient()
        result = await client.status(settings)
        console.print(result)

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to read printer status:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def _apply_job_settings(settings: Settings, quality: str, material: str | None) -> Settings:
    settings.quality = quality  # type: ignore[assignment]
    if material is not None:
        settings.material = material.upper()  # type: ignore[assignment]
    return settings


def _print_validation_report(report: ValidationReport) -> None:
    table = Table(title="Validation")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Severity")
    table.add_column("Message")
    for check in report.checks:
        table.add_row(
            check.name,
            "ok" if check.passed else "fail",
            check.severity,
            check.message,
        )
    console.print(table)
    if report.score is not None:
        console.print(f"Print Confidence Score: [bold]{report.score}%[/bold]")


@app.command("validate")
def validate_model(
    model: Path = typer.Option(..., "--model", "-m", help="Path to STL/OBJ/GLB/3MF"),
    quality: str = typer.Option("standard", "--quality", "-q"),
    material: str | None = typer.Option(None, "--material"),
) -> None:
    """Validate a model without slicing or printing."""
    settings = _apply_job_settings(load_settings(), quality, material)

    async def _run() -> None:
        report = await BambuPipeline(settings).validate_model(
            model.resolve(),
            quality=settings.quality,
            material=settings.material,
        )
        _print_validation_report(report)
        if not report.passed:
            raise typer.Exit(code=2)

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Validation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("slice")
def slice_model(
    model: Path = typer.Option(..., "--model", "-m", help="Path to STL/OBJ/GLB/3MF"),
    quality: str = typer.Option("standard", "--quality", "-q"),
    material: str | None = typer.Option(None, "--material"),
) -> None:
    """Validate and slice a model without uploading or printing."""
    settings = _apply_job_settings(load_settings(), quality, material)

    async def _run() -> None:
        job = await BambuPipeline(settings).slice_model(
            model.resolve(),
            quality=settings.quality,
            material=settings.material,
        )
        if job.artifacts.validation:
            _print_validation_report(job.artifacts.validation)
        if job.stage == JobStage.FAILED:
            console.print(f"[red]Slice skipped:[/red] {job.error or 'validation failed'}")
            raise typer.Exit(code=2)
        console.print(f"Sliced file: [bold]{job.artifacts.sliced_path}[/bold]")
        if job.artifacts.thumbnail_path:
            console.print(f"Thumbnail: [bold]{job.artifacts.thumbnail_path}[/bold]")
        if job.artifacts.estimated_print_time:
            console.print(f"Estimated time: [bold]{job.artifacts.estimated_print_time}[/bold]")
        if job.artifacts.estimated_filament_g is not None:
            filament = job.artifacts.estimated_filament_g
            console.print(f"Estimated filament: [bold]{filament:.1f}g[/bold]")

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Slicing failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("preview")
def preview_model(
    model: Path = typer.Option(..., "--model", "-m", help="Path to STL/OBJ/GLB/3MF"),
    quality: str = typer.Option("standard", "--quality", "-q"),
    material: str | None = typer.Option(None, "--material"),
) -> None:
    """Generate a local slice preview without uploading or printing."""
    slice_model(model=model, quality=quality, material=material)


@app.command("print")
def print_model(
    prompt: str = typer.Argument("", help="Text prompt for text_full mode when --model is omitted"),
    model: Path | None = typer.Option(None, "--model", "-m", help="Path to STL/GLB/3MF"),
    quality: str = typer.Option("standard", "--quality", "-q"),
    material: str | None = typer.Option(
        None,
        "--material",
        help="Material key from profiles.json, e.g. PLA, PETG, TPU",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip approval gates"),
) -> None:
    """Run mesh_only or text_full pipeline: generate/validate → slice → print."""
    settings = _apply_job_settings(_settings_ctx(auto_approve=yes), quality, material)

    if model is None and not prompt:
        console.print("[red]Provide --model for mesh_only or a text prompt for text_full[/red]")
        raise typer.Exit(code=1)

    async def _run() -> None:
        if settings.auto_approve:
            console.print(f"Checking printer LAN services at [bold]{settings.printer_ip}[/bold]...")
            await BambuPrinterClient().ensure_reachable(settings)
            console.print("[green]Printer LAN services are reachable[/green]")
        orchestrator = PipelineOrchestrator(settings)
        job = await orchestrator.create_job(
            mode="mesh_only" if model else "text_full",
            model_path=str(model.resolve()) if model else None,
            prompt=prompt,
            material=settings.material,
        )
        console.print(f"Created job [bold]{job.id}[/bold]")
        job = await orchestrator.run_mesh_pipeline(job.id)
        console.print(f"Job {job.id} finished in stage [bold]{job.stage.value}[/bold]")
        if job.stage == JobStage.DONE:
            console.print("[green]Print started successfully[/green]")
        elif job.awaits_approval:
            console.print("Job is waiting for approval — use the API or rerun with --yes")

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Pipeline failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("jobs")
def jobs_list() -> None:
    """List in-memory jobs (the local API adapter keeps its own store)."""
    settings = load_settings()

    async def _run() -> None:
        orchestrator = PipelineOrchestrator(settings)
        rows = await orchestrator.list_jobs()
        if not rows:
            console.print("No jobs")
            return
        table = Table()
        table.add_column("ID")
        table.add_column("Stage")
        table.add_column("Model")
        for job in rows:
            table.add_row(job.id, job.stage.value, job.artifacts.model_path or "-")
        console.print(table)

    asyncio.run(_run())


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host for the local adapter"),
    port: int = typer.Option(8080, "--port", help="Bind port for the local adapter"),
    reload: bool = typer.Option(False, "--reload", help="Enable uvicorn reload"),
) -> None:
    """Run the optional local REST adapter."""
    try:
        import uvicorn
    except ImportError as exc:
        console.print('[red]Install API dependencies:[/red] pip install "bambu-pipe[api]"')
        raise typer.Exit(code=1) from exc
    uvicorn.run("bambu_pipe.api:create_app", factory=True, host=host, port=port, reload=reload)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
