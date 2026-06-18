from __future__ import annotations

import json
from zipfile import ZipFile

from bambu_pipe.config import Settings
from bambu_pipe.providers.slicer.local_orca import (
    _extract_3mf_thumbnail,
    _parse_3mf_gcode_metadata,
    _patch_3mf_filament_metadata,
    _resolve_profile_files,
)


def test_patch_3mf_ams_metadata_fills_filament_ids_and_enable_ams(tmp_path) -> None:
    output = tmp_path / "print.gcode.3mf"
    settings = {
        "filament_ids": [""],
        "filament_settings_id": ["Bambu PLA Basic @BBL A1"],
    }
    with ZipFile(output, "w") as zf:
        zf.writestr("Metadata/project_settings.config", json.dumps(settings))
        zf.writestr("Metadata/plate_1.gcode", "; test")

    _patch_3mf_filament_metadata(output, use_ams=True)

    with ZipFile(output) as zf:
        patched = json.loads(zf.read("Metadata/project_settings.config"))

    assert patched["enable_ams"] == "1"
    assert patched["filament_ids"] == ["Bambu PLA Basic @BBL A1"]


def test_patch_3mf_filament_metadata_does_not_force_ams_when_disabled(tmp_path) -> None:
    output = tmp_path / "print.gcode.3mf"
    with ZipFile(output, "w") as zf:
        zf.writestr(
            "Metadata/project_settings.config",
            json.dumps({"filament_ids": [""], "filament_settings_id": ["Bambu PLA Basic"]}),
        )

    _patch_3mf_filament_metadata(output, use_ams=False)

    with ZipFile(output) as zf:
        patched = json.loads(zf.read("Metadata/project_settings.config"))

    assert "enable_ams" not in patched


def test_profile_registry_resolves_material_without_code_mapping(tmp_path) -> None:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    for filename in ("machine.json", "process_standard.json", "filament_tpu.json"):
        (profiles_dir / filename).write_text("{}", encoding="utf-8")
    (profiles_dir / "profiles.json").write_text(
        json.dumps(
            {
                "machine": "machine.json",
                "processes": {"standard": "process_standard.json"},
                "materials": {"TPU": "filament_tpu.json"},
            }
        ),
        encoding="utf-8",
    )

    settings = Settings(profiles_dir=profiles_dir, material="TPU", quality="standard")

    machine, process, filament = _resolve_profile_files(settings)
    assert machine.name == "machine.json"
    assert process.name == "process_standard.json"
    assert filament.name == "filament_tpu.json"


def test_3mf_volume_estimate_uses_profile_density(tmp_path) -> None:
    output = tmp_path / "print.gcode.3mf"
    with ZipFile(output, "w") as zf:
        zf.writestr("Metadata/project_settings.config", json.dumps({"filament_density": ["1.28"]}))
        zf.writestr("Metadata/plate_1.gcode", "; filament used [cm3] = 10.0\n")

    assert _parse_3mf_gcode_metadata(output)["estimated_filament_g"] == 12.8


def test_3mf_volume_estimate_is_omitted_without_density(tmp_path) -> None:
    output = tmp_path / "print.gcode.3mf"
    with ZipFile(output, "w") as zf:
        zf.writestr("Metadata/project_settings.config", json.dumps({}))
        zf.writestr("Metadata/plate_1.gcode", "; filament used [cm3] = 10.0\n")

    assert "estimated_filament_g" not in _parse_3mf_gcode_metadata(output)


def test_extract_3mf_thumbnail_writes_sidecar_file(tmp_path) -> None:
    output = tmp_path / "print.gcode.3mf"
    with ZipFile(output, "w") as zf:
        zf.writestr("Metadata/plate_1.png", b"image")

    thumbnail = _extract_3mf_thumbnail(output)

    assert thumbnail is not None
    assert thumbnail.name == "print.gcode.thumbnail.png"
    assert thumbnail.read_bytes() == b"image"
