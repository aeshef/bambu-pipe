"""Resolve profile inheritance before handing complete JSON settings to the CLI."""

from __future__ import annotations

import json
from pathlib import Path

from bambu_pipe.models.errors import ConfigError


def discover_resource_profiles(binary: Path, explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit.expanduser().resolve()
    candidates = [
        binary.parent.parent / "Resources" / "profiles",  # macOS bundle
        binary.parent / "resources" / "profiles",  # Windows / portable distributions
        binary.parent.parent / "share" / "OrcaSlicer" / "resources" / "profiles",
        binary.parent.parent / "share" / "BambuStudio" / "resources" / "profiles",
    ]
    return next((p for p in candidates if p.is_dir()), None)


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"Cannot read slicer profile {path.name}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Slicer profile {path.name} must be a JSON object")
    return data


def _index(local: Path, resources: Path | None) -> dict[str, Path]:
    index = {}
    if resources is not None and resources.is_dir():
        # Vendor manifests provide exact paths; do not recursively scan application data.
        # A1 presets belong to BBL. Other vendors reuse generic parent names;
        # combining their manifests would silently apply another printer's settings.
        manifest_path = resources / "BBL.json"
        if manifest_path.is_file():
            vendor = resources / "BBL"
            manifest = _read(manifest_path)
            for category in ("machine_list", "process_list", "filament_list"):
                for entry in manifest.get(category, []):
                    relative = entry.get("sub_path", "")
                    path = (vendor / relative).resolve()
                    if not path.is_relative_to(vendor.resolve()):
                        raise ConfigError("Profile manifest points outside its vendor directory")
                    if isinstance(entry.get("name"), str) and path.is_file():
                        index[entry["name"]] = path
    # Explicit local profiles override bundled names; parents can live alongside them.
    for path in sorted(local.glob("*.json")):
        data = _read(path)
        if isinstance(data.get("name"), str):
            index[data["name"]] = path
    return index


def _resolve(path: Path, index: dict[str, Path], stack: tuple[Path, ...] = ()) -> dict:
    path = path.resolve()
    if path in stack:
        raise ConfigError(f"Slicer profile inheritance cycle at {path.name}")
    data = _read(path)
    resolved = {}
    dependencies = []
    parent = data.get("inherits")
    if parent:
        if not isinstance(parent, str):
            raise ConfigError(f"Invalid inherits in {path.name}")
        dependencies.append(parent)
    includes = data.get("include", [])
    if not isinstance(includes, list) or not all(isinstance(value, str) for value in includes):
        raise ConfigError(f"Invalid include list in {path.name}")
    dependencies.extend(includes)
    for name in dependencies:
        dependency = index.get(name)
        if dependency is None:
            raise ConfigError(
                f"Missing inherited slicer profile: {name}",
                suggestion=(
                    "Export complete profiles or set BAMBU_PIPE_SLICER_RESOURCE_PROFILES_DIR "
                    "to the slicer's resources/profiles directory."
                ),
            )
        resolved.update(_resolve(dependency, index, (*stack, path)))
    resolved.update(data)
    resolved.pop("include", None)
    resolved["inherits"] = ""
    return resolved


def flatten_profiles(
    profiles: tuple[Path, Path, Path], *, resources: Path | None, output_dir: Path
) -> tuple[Path, Path, Path]:
    index = _index(profiles[0].parent, resources)
    output_dir.mkdir(parents=True, exist_ok=True)
    destinations = []
    for category, source in zip(("machine", "process", "filament"), profiles, strict=True):
        flattened = _resolve(source, index)
        destination = output_dir / f"{category}.json"
        destination.write_text(json.dumps(flattened, indent=2) + "\n", encoding="utf-8")
        destinations.append(destination)
    return tuple(destinations)  # type: ignore[return-value]
