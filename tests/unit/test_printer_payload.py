from __future__ import annotations

import pytest
from bambu_pipe.models.errors import PrinterError
from bambu_pipe.printer.client import _with_printer_retries
from bambu_pipe.printer.payload import build_project_file_payload
from bambu_pipe.printer.status import has_filament_block


def test_project_file_payload_uses_root_ftp_url() -> None:
    payload = build_project_file_payload(
        filename="cube.gcode.3mf",
        use_ams=True,
        physical_ams_slot=3,
    )

    print_payload = payload["print"]
    assert print_payload["file"] == "cube.gcode.3mf"
    assert print_payload["url"] == "ftp:///cube.gcode.3mf"
    assert print_payload["param"] == "Metadata/plate_1.gcode"
    assert print_payload["bed_leveling"] is True
    assert print_payload["sequence_id"] == "10000000"


def test_project_file_payload_maps_physical_ams_slot_to_zero_based_protocol() -> None:
    payload = build_project_file_payload(
        filename="cube.gcode.3mf",
        use_ams=True,
        physical_ams_slot=3,
    )

    assert payload["print"]["use_ams"] is True
    assert payload["print"]["ams_mapping"] == [2]


def test_project_file_payload_maps_physical_ams_slot_four() -> None:
    payload = build_project_file_payload(
        filename="cube.gcode.3mf",
        use_ams=True,
        physical_ams_slot=4,
    )

    assert payload["print"]["use_ams"] is True
    assert payload["print"]["ams_mapping"] == [3]


def test_project_file_payload_can_disable_ams() -> None:
    payload = build_project_file_payload(
        filename="cube.gcode.3mf",
        use_ams=False,
        physical_ams_slot=3,
    )

    assert payload["print"]["use_ams"] is False
    assert payload["print"]["ams_mapping"] == []


def test_external_filament_payload_does_not_request_ams_slot() -> None:
    payload = build_project_file_payload(
        filename="cube.gcode.3mf",
        use_ams=False,
        physical_ams_slot=4,
    )

    assert payload["print"] == {
        **payload["print"],
        "use_ams": False,
        "ams_mapping": [],
    }


def test_filament_block_requires_explicit_printer_error() -> None:
    report = {
        "print": {
            "print_error": 134201347,
            "ams_status": 260,
            "hw_switch_state": 1,
            "filam_bak": [6],
        }
    }

    assert has_filament_block(report) is True


def test_filament_sensor_during_ams_load_does_not_block_without_error() -> None:
    report = {
        "print": {
            "print_error": 0,
            "ams_status": 262,
            "hw_switch_state": 1,
            "filam_bak": [6],
        }
    }

    assert has_filament_block(report) is False


def test_printer_errors_are_not_retried_as_transport_errors() -> None:
    attempts = 0

    def fail() -> None:
        nonlocal attempts
        attempts += 1
        raise PrinterError("firmware rejected print")

    with pytest.raises(PrinterError, match="firmware rejected print"):
        _with_printer_retries("MQTT start_print", fail)

    assert attempts == 1
