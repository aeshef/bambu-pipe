"""Mesh validation and print confidence scoring."""

from __future__ import annotations

import asyncio
from pathlib import Path

import trimesh

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import ValidationFailedError
from bambu_pipe.models.job import PrintJob
from bambu_pipe.models.validation import ValidationCheck, ValidationReport

SUPPORTED_MODEL_SUFFIXES = {".stl", ".obj", ".glb", ".gltf", ".3mf"}
MAX_MODEL_FILE_MB = 50


def _load_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, force="mesh", process=True)
    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ValidationFailedError(f"No geometry found in {path.name}")
        return trimesh.util.concatenate(tuple(loaded.geometry.values()))
    return loaded


def _validate_sync(job: PrintJob, settings: Settings) -> ValidationReport:
    model_path = job.artifacts.model_path or job.model_path
    if not model_path:
        raise ValidationFailedError("No model file provided for validation")

    path = Path(model_path)
    checks: list[ValidationCheck] = []

    if not path.exists():
        checks.append(
            ValidationCheck(
                name="file_exists",
                passed=False,
                message=f"File not found: {path}",
                severity="error",
            )
        )
        return ValidationReport(checks=checks)

    suffix = path.suffix.lower()
    checks.append(
        ValidationCheck(
            name="supported_format",
            passed=suffix in SUPPORTED_MODEL_SUFFIXES,
            message=f"Format {suffix or '(none)'}",
            severity="error",
            suggestion="Use STL, OBJ, GLB, or 3MF",
        )
    )
    if suffix not in SUPPORTED_MODEL_SUFFIXES:
        return ValidationReport(checks=checks, score=_confidence_score(checks))

    file_size_mb = path.stat().st_size / (1024 * 1024)
    checks.append(
        ValidationCheck(
            name="file_size",
            passed=file_size_mb <= MAX_MODEL_FILE_MB,
            message=f"{file_size_mb:.1f} MB (max {MAX_MODEL_FILE_MB} MB)",
            severity="error",
            suggestion="Simplify the mesh or upload a smaller file",
        )
    )

    try:
        mesh = _load_mesh(path)
    except Exception as exc:  # noqa: BLE001 — surface load errors as validation checks
        checks.append(
            ValidationCheck(
                name="mesh_load",
                passed=False,
                message=str(exc),
                severity="error",
            )
        )
        return ValidationReport(checks=checks, score=_confidence_score(checks))

    bounds = mesh.bounds
    size = bounds[1] - bounds[0]
    fits_bed = (
        float(size[0]) <= settings.bed_width_mm
        and float(size[1]) <= settings.bed_depth_mm
        and float(size[2]) <= settings.bed_height_mm
    )
    checks.append(
        ValidationCheck(
            name="bed_fit",
            passed=fits_bed,
            message=(
                f"Dimensions {size[0]:.1f}×{size[1]:.1f}×{size[2]:.1f} mm "
                f"(max {settings.bed_width_mm:.0f}×{settings.bed_depth_mm:.0f}×"
                f"{settings.bed_height_mm:.0f})"
            ),
            severity="error",
            suggestion="Scale the model down before slicing",
        )
    )

    is_watertight = bool(mesh.is_watertight)
    watertight_message = (
        "Mesh is watertight" if is_watertight else "Mesh has holes or non-manifold geometry"
    )
    checks.append(
        ValidationCheck(
            name="watertight",
            passed=is_watertight,
            message=watertight_message,
            severity="warning",
            suggestion="Repair the mesh or regenerate with printability constraints",
        )
    )

    try:
        component_count = len(mesh.split(only_watertight=False))
    except ImportError:
        component_count = None
    checks.append(
        ValidationCheck(
            name="connected_components",
            passed=component_count is None or component_count <= 1,
            message=(
                "Graph backend unavailable"
                if component_count is None
                else f"{component_count} component(s)"
            ),
            severity="info" if component_count is None else "warning",
            suggestion=(
                "Install trimesh graph extras for disconnected-part checks"
                if component_count is None
                else "Merge disconnected parts or verify they are intentional"
            ),
        )
    )

    return ValidationReport(checks=checks, score=_confidence_score(checks))


def _confidence_score(checks: list[ValidationCheck]) -> int:
    score = 100
    for check in checks:
        if check.passed:
            continue
        score -= 45 if check.severity == "error" else 15
    return max(0, min(100, score))


class DefaultValidationStage:
    async def run(self, job: PrintJob, settings: Settings) -> ValidationReport:
        return await asyncio.to_thread(_validate_sync, job, settings)
