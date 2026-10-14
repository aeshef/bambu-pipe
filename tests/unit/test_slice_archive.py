from zipfile import ZipFile

import pytest
from bambu_pipe.models.errors import SliceError
from bambu_pipe.providers.slicer.local_orca import validate_sliced_archive


@pytest.mark.parametrize("contents", [b"not a zip", b""])
def test_rejects_invalid_archives(tmp_path, contents):
    path = tmp_path / "slice.3mf"
    path.write_bytes(contents)
    with pytest.raises(SliceError, match="Invalid sliced archive"):
        validate_sliced_archive(path)


@pytest.mark.parametrize(
    "plates", [[], ["Metadata/plate_2.gcode"], ["Metadata/plate_1.gcode", "Metadata/plate_2.gcode"]]
)
def test_requires_the_single_plate_referenced_by_printer_payload(tmp_path, plates):
    path = tmp_path / "slice.3mf"
    with ZipFile(path, "w") as archive:
        archive.writestr("3D/3dmodel.model", "unsliced geometry")
        for plate in plates:
            archive.writestr(plate, "G1 X1 E0.4\n")
    with pytest.raises(SliceError, match="exactly one sliced plate"):
        validate_sliced_archive(path)


@pytest.mark.parametrize("gcode", ["; G1 X1 E0.4\n", "G1 X1 Y2\n", "G1 X1 E0\n"])
def test_comment_or_travel_only_gcode_is_not_a_slice(tmp_path, gcode):
    path = tmp_path / "slice.3mf"
    with ZipFile(path, "w") as archive:
        archive.writestr("Metadata/plate_1.gcode", gcode)
    with pytest.raises(SliceError, match="no extrusion"):
        validate_sliced_archive(path)


def test_accepts_extrusion_and_detects_corrupt_gcode(tmp_path):
    path = tmp_path / "slice.3mf"
    with ZipFile(path, "w") as archive:
        archive.writestr("Metadata/plate_1.gcode", "M83\nG1 X1 Y2 E0.4\n")
    validate_sliced_archive(path)
    raw = path.read_bytes()
    assert b"G1 X1 Y2 E0.4" in raw
    path.write_bytes(raw.replace(b"G1 X1 Y2 E0.4", b"G1 X1 Y2 E0.9"))
    with pytest.raises(SliceError, match="corrupt entry"):
        validate_sliced_archive(path)


def test_rejects_plate_temperature_profile_mismatch(tmp_path):
    path = tmp_path / "slice.3mf"
    with ZipFile(path, "w") as archive:
        archive.writestr("Metadata/plate_1.gcode", "G1 X1 E0.2\n")
        archive.writestr("Metadata/project_settings.config", '{"curr_bed_type": "Cool Plate"}')
    with pytest.raises(SliceError, match="bed type does not match"):
        validate_sliced_archive(path, expected_bed_type="Textured PEI Plate")
