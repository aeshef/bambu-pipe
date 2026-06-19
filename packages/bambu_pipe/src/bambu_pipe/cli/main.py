"""Command-line interface."""

from __future__ import annotations

import asyncio
import json
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
from bambu_pipe.storage.sqlite import SQLiteJobStore

app = typer.Typer(no_args_is_help=True, add_completion=False)
jobs_app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
    help="Inspect persisted jobs",
)
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


def _cli_orchestrator(settings: Settings) -> PipelineOrchestrator:
    return PipelineOrchestrator(settings, store=SQLiteJobStore(settings.database_path))


def _cli_pipeline(settings: Settings) -> BambuPipeline:
    return BambuPipeline(settings=settings, orchestrator=_cli_orchestrator(settings))


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


def _job_payload(job) -> dict[str, object]:  # noqa: ANN001
    return job.model_dump(mode="json")


def _print_json(payload: object) -> None:
    console.print(json.dumps(payload, indent=2, sort_keys=True))


def _print_plan_summary(job) -> None:  # noqa: ANN001
    console.print(f"Job: [bold]{job.id}[/bold]")
    console.print(f"Stage: [bold]{job.stage.value}[/bold]")
    console.print(f"Material: [bold]{job.material}[/bold]  Quality: [bold]{job.quality}[/bold]")
    if job.artifacts.model_dimensions_mm:
        dims = " x ".join(f"{value:.1f}mm" for value in job.artifacts.model_dimensions_mm)
        console.print(f"Dimensions: [bold]{dims}[/bold]")
    if job.artifacts.estimated_print_time:
        console.print(f"Estimated time: [bold]{job.artifacts.estimated_print_time}[/bold]")
    if job.artifacts.estimated_filament_g is not None:
        console.print(f"Estimated filament: [bold]{job.artifacts.estimated_filament_g:.1f}g[/bold]")
    if job.artifacts.validation:
        _print_validation_report(job.artifacts.validation)
    if job.artifacts.preview_html_path:
        console.print(f"Preview HTML: [bold]{job.artifacts.preview_html_path}[/bold]")
    if job.artifacts.artifact_manifest_path:
        console.print(f"Artifact manifest: [bold]{job.artifacts.artifact_manifest_path}[/bold]")


@app.command("validate")
def validate_model(
    model: Path = typer.Option(..., "--model", "-m", help="Path to STL/OBJ/GLB/3MF"),
    quality: str = typer.Option("standard", "--quality", "-q"),
    material: str | None = typer.Option(None, "--material"),
) -> None:
    """Validate a model without slicing or printing."""
    settings = _apply_job_settings(load_settings(), quality, material)

    async def _run() -> None:
        report = await _cli_pipeline(settings).validate_model(
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
        job = await _cli_pipeline(settings).slice_model(
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
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable job JSON"),
) -> None:
    """Generate a local slice preview without uploading or printing."""
    settings = _apply_job_settings(load_settings(), quality, material)

    async def _run() -> None:
        job = await _cli_pipeline(settings).slice_model(
            model.resolve(),
            quality=settings.quality,
            material=settings.material,
        )
        if json_output:
            _print_json(_job_payload(job))
            return
        _print_plan_summary(job)
        if job.stage == JobStage.FAILED:
            raise typer.Exit(code=2)

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Preview failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


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
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan through slicing without printing"),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable job JSON"),
) -> None:
    """Run mesh_only or text_full pipeline: generate/validate → slice → print."""
    settings = _apply_job_settings(_settings_ctx(auto_approve=yes), quality, material)

    if model is None and not prompt:
        console.print("[red]Provide --model for mesh_only or a text prompt for text_full[/red]")
        raise typer.Exit(code=1)

    async def _run() -> None:
        if dry_run:
            job = await _cli_pipeline(settings).plan_print(
                prompt=prompt,
                model_path=model.resolve() if model else None,
                quality=settings.quality,
                material=settings.material,
            )
            if json_output:
                _print_json(_job_payload(job))
            else:
                console.print(
                    "[green]Dry-run print plan complete. Printer was not contacted.[/green]"
                )
                _print_plan_summary(job)
            if job.stage == JobStage.FAILED:
                raise typer.Exit(code=2)
            return
        if settings.auto_approve:
            console.print(f"Checking printer LAN services at [bold]{settings.printer_ip}[/bold]...")
            await BambuPrinterClient().ensure_reachable(settings)
            console.print("[green]Printer LAN services are reachable[/green]")
        orchestrator = _cli_orchestrator(settings)
        job = await orchestrator.create_job(
            mode="mesh_only" if model else "text_full",
            model_path=str(model.resolve()) if model else None,
            prompt=prompt,
            material=settings.material,
        )
        console.print(f"Created job [bold]{job.id}[/bold]")
        job = await orchestrator.run_mesh_pipeline(job.id)
        if json_output:
            _print_json(_job_payload(job))
            return
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


@jobs_app.callback()
def jobs_list(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """List persisted jobs from the configured SQLite store."""
    if ctx.invoked_subcommand is not None:
        return
    settings = load_settings()

    async def _run() -> None:
        orchestrator = _cli_orchestrator(settings)
        rows = await orchestrator.list_jobs()
        if json_output:
            _print_json([_job_payload(job) for job in rows])
            return
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


@jobs_app.command("show")
def jobs_show(
    job_id: str,
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """Show a persisted job."""
    settings = load_settings()

    async def _run() -> None:
        job = await _cli_orchestrator(settings).get_job(job_id)
        if job is None:
            console.print(f"[red]Unknown job:[/red] {job_id}")
            raise typer.Exit(code=1)
        if json_output:
            _print_json(_job_payload(job))
            return
        _print_plan_summary(job)

    asyncio.run(_run())


@jobs_app.command("artifacts")
def jobs_artifacts(
    job_id: str,
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """Show job artifact paths."""
    settings = load_settings()

    async def _run() -> None:
        job = await _cli_orchestrator(settings).get_job(job_id)
        if job is None:
            console.print(f"[red]Unknown job:[/red] {job_id}")
            raise typer.Exit(code=1)
        artifacts = {
            key: value
            for key, value in job.artifacts.model_dump(mode="json").items()
            if value not in (None, [], {})
        }
        if json_output:
            _print_json(artifacts)
            return
        table = Table(title=f"Artifacts for {job.id}")
        table.add_column("Name")
        table.add_column("Value")
        for key, value in artifacts.items():
            table.add_row(key, json.dumps(value) if isinstance(value, (dict, list)) else str(value))
        console.print(table)

    asyncio.run(_run())


@jobs_app.command("retry")
def jobs_retry(
    job_id: str,
    run: bool = typer.Option(False, "--run", help="Run the retried job immediately"),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """Create a new job from an existing job's prompt or model artifact."""
    settings = load_settings()

    async def _run() -> None:
        orchestrator = _cli_orchestrator(settings)
        old = await orchestrator.get_job(job_id)
        if old is None:
            console.print(f"[red]Unknown job:[/red] {job_id}")
            raise typer.Exit(code=1)
        model_path = old.artifacts.model_path or old.model_path
        new = await orchestrator.create_job(
            mode=old.mode,
            prompt=old.prompt,
            model_path=model_path if old.mode == "mesh_only" else None,
            quality=old.quality,
            material=old.material,
            auto_approve=False,
        )
        if run:
            new = await orchestrator.run_mesh_pipeline(new.id)
        if json_output:
            _print_json(_job_payload(new))
            return
        console.print(f"Created retry job [bold]{new.id}[/bold] from [bold]{old.id}[/bold]")
        console.print(f"Stage: [bold]{new.stage.value}[/bold]")

    asyncio.run(_run())


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host for the local adapter"),
    port: int = typer.Option(8080, "--port", help="Bind port for the local adapter"),
    reload: bool = typer.Option(False, "--reload", help="Enable uvicorn reload"),
    unsafe_bind: bool = typer.Option(
        False,
        "--i-understand-local-network-risk",
        help="Allow binding the unauthenticated local adapter beyond loopback",
    ),
) -> None:
    """Run the optional local REST adapter."""
    settings = load_settings()
    if not _is_loopback_host(host) and not settings.secret(settings.api_token) and not unsafe_bind:
        console.print(
            "[red]Refusing to bind the local REST adapter beyond loopback without "
            "BAMBU_PIPE_API_TOKEN.[/red]"
        )
        console.print(
            "Set BAMBU_PIPE_API_TOKEN or pass --i-understand-local-network-risk explicitly."
        )
        raise typer.Exit(code=2)
    try:
        import uvicorn
    except ImportError as exc:
        console.print('[red]Install API dependencies:[/red] pip install "bambu-pipe[api]"')
        raise typer.Exit(code=1) from exc
    uvicorn.run("bambu_pipe.api:create_app", factory=True, host=host, port=port, reload=reload)


def _is_loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "localhost"}


app.add_typer(jobs_app, name="jobs")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
