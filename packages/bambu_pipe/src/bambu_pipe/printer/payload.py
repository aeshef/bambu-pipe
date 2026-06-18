"""Bambu printer MQTT payload builders."""

from __future__ import annotations


def build_project_file_payload(
    *,
    filename: str,
    use_ams: bool,
    physical_ams_slot: int,
) -> dict[str, object]:
    """Build Bambu's single-material ``project_file`` command.

    User-facing AMS slots are physical 1..4 inputs. Bambu's MQTT protocol
    expects zero-based indices in ``ams_mapping``.
    """
    ams_mapping = [physical_ams_slot - 1] if use_ams else []
    return {
        "print": {
            "command": "project_file",
            "param": "Metadata/plate_1.gcode",
            "file": filename,
            "bed_leveling": True,
            "bed_type": "textured_plate",
            "flow_cali": True,
            "vibration_cali": True,
            "url": f"ftp:///{filename}",
            "layer_inspect": False,
            "use_ams": use_ams,
            "ams_mapping": ams_mapping,
            "sequence_id": "10000000",
        }
    }
