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
    dimensions = [float(size[0]), float(size[1]), float(size[2])]
    job.artifacts.model_dimensions_mm = dimensions
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
    checks.extend(_scale_sanity_checks(dimensions, settings))
    checks.append(_bed_contact_check(mesh))
    checks.append(_overhang_check(mesh))
    checks.append(_thin_feature_check(mesh, dimensions))

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


def _scale_sanity_checks(dimensions: list[float], settings: Settings) -> list[ValidationCheck]:
    max_dim = max(dimensions)
    min_dim = min((value for value in dimensions if value > 0), default=0.0)
    bed_max = max(settings.bed_width_mm, settings.bed_depth_mm, settings.bed_height_mm)
    return [
        ValidationCheck(
            name="scale_not_tiny",
            passed=max_dim >= 5.0,
            message=f"Largest dimension is {max_dim:.1f} mm",
            severity="warning",
            suggestion="Scale up if the model was exported in centimeters/meters by mistake",
        ),
        ValidationCheck(
            name="scale_not_huge",
            passed=max_dim <= bed_max * 0.9,
            message=f"Largest dimension is {max_dim:.1f} mm",
            severity="warning",
            suggestion="Scale down or split the model for a safer print margin",
        ),
        ValidationCheck(
            name="thin_axis_sanity",
            passed=min_dim >= 0.8,
            message=f"Smallest bounding-box axis is {min_dim:.2f} mm",
            severity="warning",
            suggestion="Very thin features may not survive slicing with a 0.4 mm nozzle",
        ),
    ]


def _bed_contact_check(mesh: trimesh.Trimesh) -> ValidationCheck:
    min_z = float(mesh.bounds[0][2])
    vertices = mesh.vertices
    if len(vertices) == 0:
        contact_ratio = 0.0
    else:
        near_bottom = abs(vertices[:, 2] - min_z) <= 0.2
        contact_ratio = float(near_bottom.sum()) / float(len(vertices))
    passed = contact_ratio >= 0.03
    return ValidationCheck(
        name="bed_contact",
        passed=passed,
        message=f"{contact_ratio:.1%} of vertices are near the lowest Z plane",
        severity="warning",
        suggestion="Prefer a flat bottom or add supports/brim if contact is small",
    )


def _overhang_check(mesh: trimesh.Trimesh) -> ValidationCheck:
    if len(mesh.faces) == 0 or len(mesh.face_normals) == 0:
        ratio = 0.0
    else:
        downward = mesh.face_normals[:, 2] < -0.35
        total_area = float(mesh.area_faces.sum()) or 1.0
        ratio = float(mesh.area_faces[downward].sum()) / total_area
    passed = ratio <= 0.25
    return ValidationCheck(
        name="overhang_risk",
        passed=passed,
        message=f"{ratio:.1%} downward-facing surface area",
        severity="warning",
        suggestion="Use supports or regenerate with flatter overhangs if this is high",
    )


def _thin_feature_check(mesh: trimesh.Trimesh, dimensions: list[float]) -> ValidationCheck:
    if len(mesh.edges_unique_length) == 0:
        shortest = min(dimensions)
    else:
        shortest = float(mesh.edges_unique_length.min())
    passed = shortest >= 0.35
    return ValidationCheck(
        name="thin_feature_risk",
        passed=passed,
        message=f"Shortest mesh edge is about {shortest:.2f} mm",
        severity="warning",
        suggestion="Thin details below nozzle width can disappear or break",
    )


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
