"""Headless OrcaSlicer integration."""

from __future__ import annotations

import asyncio
import json
import re
import struct
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import ConfigError, SliceError
from bambu_pipe.providers.slicer.base import SliceResult
from bambu_pipe.providers.slicer.discovery import discover_orca_slicer

DEFAULT_PROFILE_REGISTRY = "profiles.json"


def _parse_slice_output(stdout: str) -> dict[str, str | float]:
    info: dict[str, str | float] = {}
    time_match = re.search(r"total estimated time:\s*(.+)", stdout, re.IGNORECASE)
    if time_match:
        info["estimated_print_time"] = time_match.group(1).strip()

    filament_match = re.search(r"total filament used \[g\]:\s*([\d.]+)", stdout, re.IGNORECASE)
    if filament_match:
        info["estimated_filament_g"] = float(filament_match.group(1))
    return info


def _parse_3mf_gcode_metadata(output_path: Path) -> dict[str, str | float]:
    """Extract print estimates from the G-code embedded in a Bambu .gcode.3mf."""
    info: dict[str, str | float] = {}
    try:
        with ZipFile(output_path) as zf:
            gcode_name = next(
                name
                for name in zf.namelist()
                if name.startswith("Metadata/plate_") and name.endswith(".gcode")
            )
            gcode = zf.read(gcode_name).decode("utf-8", errors="replace")
    except (OSError, StopIteration, KeyError):
        return info

    time_match = re.search(
        r";\s*model printing time:\s*([^;]+);\s*total estimated time:\s*(.+)",
        gcode,
    )
    if time_match:
        info["estimated_print_time"] = time_match.group(2).strip()

    grams_match = re.search(r";\s*filament used \[g\]\s*=\s*([\d.]+)", gcode, re.IGNORECASE)
    if grams_match:
        info["estimated_filament_g"] = float(grams_match.group(1))
        return info

    volume_match = re.search(r";\s*filament used \[cm3\]\s*=\s*([\d.]+)", gcode, re.IGNORECASE)
    if volume_match:
        density = _parse_3mf_filament_density(output_path)
        if density is not None:
            info["estimated_filament_g"] = float(volume_match.group(1)) * density
    return info


def _parse_3mf_filament_density(output_path: Path) -> float | None:
    try:
        with ZipFile(output_path) as zf:
            settings = json.loads(zf.read("Metadata/project_settings.config"))
    except (OSError, KeyError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    densities = settings.get("filament_density")
    if isinstance(densities, list) and densities:
        try:
            return float(densities[0])
        except (TypeError, ValueError):
            return None
    if isinstance(densities, str):
        try:
            return float(densities)
        except ValueError:
            return None
    return None


def _extract_3mf_thumbnail(output_path: Path) -> Path | None:
    try:
        with ZipFile(output_path) as zf:
            candidates = [
                name
                for name in zf.namelist()
                if name.lower().endswith((".png", ".jpg", ".jpeg"))
                and ("thumbnail" in name.lower() or name.startswith("Metadata/"))
            ]
            if not candidates:
                return None
            source_name = sorted(
                candidates,
                key=lambda value: ("thumbnail" not in value.lower(), value),
            )[0]
            suffix = Path(source_name).suffix or ".png"
            destination = output_path.with_suffix(f".thumbnail{suffix}")
            destination.write_bytes(zf.read(source_name))
            return destination
    except (OSError, KeyError):
        return None


def _patch_3mf_filament_metadata(output_path: Path, *, use_ams: bool) -> None:
    """Fill missing filament IDs without changing the sliced material."""
    try:
        with ZipFile(output_path) as source:
            entries = {name: source.read(name) for name in source.namelist()}
    except OSError:
        return

    settings_name = "Metadata/project_settings.config"
    raw_settings = entries.get(settings_name)
    if raw_settings is None:
        return

    try:
        settings = json.loads(raw_settings.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return

    filament_ids = settings.get("filament_ids")
    if isinstance(filament_ids, list):
        settings["filament_ids"] = [
            value or _fallback_filament_id(settings, index)
            for index, value in enumerate(filament_ids)
        ]
    elif not filament_ids:
        settings["filament_ids"] = [_fallback_filament_id(settings, 0)]

    if use_ams:
        settings["enable_ams"] = "1"
    entries[settings_name] = json.dumps(settings, indent=4).encode("utf-8")

    with NamedTemporaryFile(dir=output_path.parent, suffix=".3mf", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with ZipFile(tmp_path, "w", compression=ZIP_DEFLATED) as target:
            for name, data in entries.items():
                target.writestr(name, data)
        tmp_path.replace(output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _fallback_filament_id(settings: dict[str, object], index: int) -> str:
    candidates = (
        settings.get("filament_settings_id"),
        settings.get("default_filament_profile"),
        settings.get("filament_type"),
    )
    for candidate in candidates:
        if isinstance(candidate, list) and index < len(candidate) and candidate[index]:
            return str(candidate[index])
        if isinstance(candidate, str) and candidate:
            return candidate
    return "Generic"


def _prescale_stl(stl_path: Path, scale: float) -> Path:
    data = stl_path.read_bytes()
    if len(data) < 84:
        return stl_path
    n_triangles = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + n_triangles * 50
    if len(data) != expected:
        return stl_path

    out = bytearray(data)
    for i in range(n_triangles):
        base = 84 + i * 50
        for j in range(3, 12):
            offset = base + j * 4
            val = struct.unpack_from("<f", out, offset)[0]
            struct.pack_into("<f", out, offset, val * scale)

    scaled = stl_path.with_stem(stl_path.stem + "_scaled")
    scaled.write_bytes(bytes(out))
    return scaled


def _maybe_prescale_for_meters(model_path: Path) -> Path:
    if model_path.suffix.lower() != ".stl":
        return model_path
    try:
        import trimesh

        mesh = trimesh.load(model_path, force="mesh", process=False)
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        size = mesh.bounds[1] - mesh.bounds[0]
        if float(max(size)) < 10.0:
            return _prescale_stl(model_path, 100.0)
    except Exception:  # noqa: BLE001
        return model_path
    return model_path


def _load_profile_registry(profiles_dir: Path) -> dict[str, Any]:
    registry_path = profiles_dir / DEFAULT_PROFILE_REGISTRY
    if not registry_path.is_file():
        raise ConfigError(
            f"Missing slicer profile registry: {registry_path}",
            suggestion=(
                "Create profiles.json with machine, processes, and materials mappings. "
                "See profiles/README.md."
            ),
        )
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Invalid slicer profile registry: {registry_path}",
            suggestion=str(exc),
        ) from exc
    if not isinstance(registry, dict):
        raise ConfigError(f"Invalid slicer profile registry: {registry_path}")
    return registry


def _registry_file(
    registry: dict[str, Any],
    section: str,
    key: str,
    *,
    profiles_dir: Path,
) -> Path:
    values = registry.get(section)
    if not isinstance(values, dict):
        raise ConfigError(f"Missing '{section}' section in {DEFAULT_PROFILE_REGISTRY}")
    filename = values.get(key)
    if not isinstance(filename, str) or not filename:
        raise ConfigError(
            f"Unsupported {section[:-1]}: {key}",
            suggestion=f"Configured {section}: {', '.join(sorted(map(str, values)))}",
        )
    return profiles_dir / filename


def _resolve_profile_files(settings: Settings) -> tuple[Path, Path, Path]:
    profiles_dir = settings.resolved_profiles_dir
    registry = _load_profile_registry(profiles_dir)
    machine_name = registry.get("machine")
    if not isinstance(machine_name, str) or not machine_name:
        raise ConfigError(f"Missing 'machine' entry in {DEFAULT_PROFILE_REGISTRY}")
    machine = profiles_dir / machine_name
    filament = _registry_file(
        registry,
        "materials",
        settings.material.upper(),
        profiles_dir=profiles_dir,
    )
    process = _registry_file(
        registry,
        "processes",
        settings.quality,
        profiles_dir=profiles_dir,
    )

    missing = [p for p in (machine, filament, process) if not p.is_file()]
    if missing:
        names = ", ".join(p.name for p in missing)
        raise ConfigError(
            f"Missing slicer profiles in {profiles_dir}: {names}",
            suggestion="Export OrcaSlicer profiles — see profiles/README.md",
        )
    return machine, process, filament


def _slice_sync(
    *,
    binary: Path,
    model_path: Path,
    output_path: Path,
    settings: Settings,
) -> SliceResult:
    machine, process, filament = _resolve_profile_files(settings)
    input_path = _maybe_prescale_for_meters(model_path)

    cmd = [
        str(binary),
        "--arrange",
        "1",
        "--orient",
        "1",
        "--load-settings",
        f"{machine};{process}",
        "--load-filaments",
        str(filament),
        "--slice",
        "0",
        "--export-3mf",
        str(output_path),
        str(input_path),
    ]

    proc = __import__("subprocess").run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    combined = f"{proc.stdout}\n{proc.stderr}"
    if proc.returncode != 0:
        raise SliceError(
            f"OrcaSlicer failed (exit {proc.returncode}): {proc.stderr[:1000]}",
            suggestion="Run `bambu-pipe doctor` to verify slicer and profiles",
        )
    if not output_path.is_file():
        raise SliceError("OrcaSlicer finished without producing a .3mf file")

    _patch_3mf_filament_metadata(output_path, use_ams=settings.use_ams)
    meta = _parse_slice_output(combined)
    meta.update({k: v for k, v in _parse_3mf_gcode_metadata(output_path).items() if v})
    thumbnail_path = _extract_3mf_thumbnail(output_path)
    return SliceResult(
        output_path=output_path,
        estimated_print_time=meta.get("estimated_print_time"),  # type: ignore[arg-type]
        estimated_filament_g=meta.get("estimated_filament_g"),  # type: ignore[arg-type]
        thumbnail_path=thumbnail_path,
    )


class LocalOrcaSlicer:
    def __init__(self, binary: Path | None = None) -> None:
        self._binary = binary

    def resolve_binary(self, settings: Settings) -> Path:
        binary = self._binary or settings.slicer_binary
        discovered = discover_orca_slicer(binary)
        if discovered is None:
            raise ConfigError(
                "Slicer binary not found (OrcaSlicer or Bambu Studio)",
                suggestion=(
                    "Install OrcaSlicer, open Bambu Studio, or set "
                    "BAMBU_PIPE_SLICER_BINARY to the slicer executable"
                ),
            )
        return discovered

    async def slice(self, model_path: Path, output_path: Path, settings: Settings) -> SliceResult:
        binary = self.resolve_binary(settings)
        return await asyncio.to_thread(
            _slice_sync,
            binary=binary,
            model_path=model_path,
            output_path=output_path,
            settings=settings,
        )
