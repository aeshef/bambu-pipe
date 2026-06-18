"""Environment and dependency checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bambu_pipe.config import Settings
from bambu_pipe.providers.slicer.discovery import discover_orca_slicer


@dataclass(slots=True)
class DoctorCheck:
    name: str
    ok: bool
    message: str
    suggestion: str | None = None


@dataclass(slots=True)
class DoctorReport:
    checks: list[DoctorCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


def run_doctor(settings: Settings | None = None) -> DoctorReport:
    settings = settings or Settings()
    report = DoctorReport()

    report.checks.append(_check_printer_config(settings))
    report.checks.append(_check_slicer(settings))
    report.checks.append(_check_profiles(settings))
    report.checks.append(_check_staging(settings))
    return report


def _check_printer_config(settings: Settings) -> DoctorCheck:
    if settings.printer_configured:
        return DoctorCheck(
            name="printer",
            ok=True,
            message=f"Printer configured ({settings.printer_model} @ {settings.printer_ip})",
        )
    return DoctorCheck(
        name="printer",
        ok=False,
        message="Printer connection is not fully configured",
        suggestion="Set BAMBU_PIPE_PRINTER_IP, PRINTER_SERIAL, PRINTER_ACCESS_CODE",
    )


def _check_slicer(settings: Settings) -> DoctorCheck:
    binary = discover_orca_slicer(settings.slicer_binary)
    if binary is None:
        return DoctorCheck(
            name="slicer",
            ok=False,
            message="Slicer binary not found (OrcaSlicer or Bambu Studio)",
            suggestion="Install a slicer or set BAMBU_PIPE_SLICER_BINARY",
        )
    label = "Bambu Studio" if binary.name == "BambuStudio" else "OrcaSlicer"
    return DoctorCheck(name="slicer", ok=True, message=f"{label} found at {binary}")


def _check_profiles(settings: Settings) -> DoctorCheck:
    profiles_dir = settings.resolved_profiles_dir
    required = [
        "machine.json",
        "filament_pla.json",
        "process_standard.json",
    ]
    missing = [name for name in required if not (profiles_dir / name).is_file()]
    if missing:
        return DoctorCheck(
            name="profiles",
            ok=False,
            message=f"Missing profiles in {profiles_dir}: {', '.join(missing)}",
            suggestion="Export OrcaSlicer profiles — see profiles/README.md",
        )
    return DoctorCheck(name="profiles", ok=True, message=f"Profiles found in {profiles_dir}")


def _check_staging(settings: Settings) -> DoctorCheck:
    path: Path = settings.staging_dir
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
    except OSError as exc:
        return DoctorCheck(
            name="staging",
            ok=False,
            message=f"Cannot write to staging dir {path}: {exc}",
        )
    return DoctorCheck(name="staging", ok=True, message=f"Writable staging dir: {path}")
