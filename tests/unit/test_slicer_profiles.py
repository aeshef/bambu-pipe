from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
import trimesh
from bambu_pipe.models.errors import ConfigError, SliceError
from bambu_pipe.providers.slicer.local_orca import _slice_sync
from bambu_pipe.providers.slicer.profiles import flatten_profiles


def write_profile(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    return path


def test_inheritance_uses_bbl_parents_and_preserves_local_overrides(tmp_path) -> None:
    resources = tmp_path / "resources"
    for vendor, diameter in [("BBL", "1.75"), ("Other", "2.85")]:
        write_profile(
            resources / f"{vendor}.json",
            {"filament_list": [{"name": "common", "sub_path": "filament/common.json"}]},
        )
        write_profile(
            resources / vendor / "filament" / "common.json",
            {"name": "common", "filament_diameter": [diameter], "nozzle_temperature": ["200"]},
        )
    local = tmp_path / "local"
    machine = write_profile(local / "machine.json", {"name": "A1", "type": "machine"})
    process = write_profile(local / "process.json", {"name": "standard", "type": "process"})
    filament = write_profile(
        local / "filament.json",
        {"name": "PLA", "inherits": "common", "nozzle_temperature": ["210"]},
    )
    flattened = flatten_profiles(
        (machine, process, filament), resources=resources, output_dir=tmp_path / "resolved"
    )
    data = json.loads(flattened[2].read_text())
    assert data["filament_diameter"] == ["1.75"]
    assert data["nozzle_temperature"] == ["210"]
    assert data["inherits"] == "" and data["name"] == "PLA"


def test_missing_parent_and_cycles_fail_before_slicer_launch(tmp_path) -> None:
    a = write_profile(tmp_path / "a.json", {"name": "A", "inherits": "missing"})
    b = write_profile(tmp_path / "b.json", {"name": "B", "inherits": "A"})
    c = write_profile(tmp_path / "c.json", {"name": "C"})
    with pytest.raises(ConfigError, match="Missing inherited"):
        flatten_profiles((a, b, c), resources=None, output_dir=tmp_path / "resolved")
    write_profile(a, {"name": "A", "inherits": "B"})
    with pytest.raises(ConfigError, match="cycle"):
        flatten_profiles((a, b, c), resources=None, output_dir=tmp_path / "resolved")


def test_slicer_keeps_small_model_dimensions_and_orientation(
    tmp_path, tmp_settings, monkeypatch
) -> None:
    local = tmp_path / "local"
    profiles = tuple(
        write_profile(local / f"{name}.json", {"name": name})
        for name in ["machine", "process", "filament"]
    )
    monkeypatch.setattr(
        "bambu_pipe.providers.slicer.local_orca._resolve_profile_files", lambda settings: profiles
    )
    model = tmp_path / "five-mm-cube.stl"
    trimesh.creation.box(extents=[5, 5, 5]).export(model)
    original = model.read_bytes()
    output = tmp_path / "slice.gcode.3mf"
    captured = []

    def run(command, **kwargs):
        captured.append(command)
        with ZipFile(output, "w") as archive:
            archive.writestr("Metadata/project_settings.config", "{}")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", run)
    _slice_sync(
        binary=tmp_path / "fake-slicer", model_path=model, output_path=output, settings=tmp_settings
    )
    assert captured[0][-1] == str(model)
    assert captured[0][captured[0].index("--orient") + 1] == "0"
    assert model.read_bytes() == original
    assert not list(tmp_path.glob("*_scaled.stl"))
    assert trimesh.load(model).extents.tolist() == pytest.approx([5, 5, 5])


def test_native_crash_has_actionable_message(tmp_path, tmp_settings, monkeypatch) -> None:
    local = tmp_path / "local"
    profiles = tuple(
        write_profile(local / f"{name}.json", {"name": name})
        for name in ["machine", "process", "filament"]
    )
    monkeypatch.setattr(
        "bambu_pipe.providers.slicer.local_orca._resolve_profile_files", lambda settings: profiles
    )
    monkeypatch.setattr(
        "subprocess.run", lambda *a, **k: SimpleNamespace(returncode=-11, stdout="", stderr="")
    )
    with pytest.raises(SliceError, match="crashed with signal 11") as error:
        _slice_sync(
            binary=tmp_path / "BambuStudio",
            model_path=tmp_path / "model.stl",
            output_path=tmp_path / "output.3mf",
            settings=tmp_settings,
        )
    assert "BAMBU_PIPE_SLICER_BINARY" in error.value.suggestion
