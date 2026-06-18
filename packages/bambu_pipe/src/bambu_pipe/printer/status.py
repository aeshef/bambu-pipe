"""Printer status reading and report helpers."""

from __future__ import annotations

import json
import socket
import ssl
import time
import uuid
from typing import Any

from bambu_pipe.models.errors import PrinterError

FILAMENT_BLOCK_ERROR_CODE = 134201347
EXTERNAL_FILAMENT_MISSING_ERROR_CODE = 134201350
PRINT_ERROR_DESCRIPTIONS = {
    302022662: "1200-8006: Failed to feed the filament into the toolhead",
    134184966: "07FF-8006: Please feed filament into the PTFE tube",
    134201347: "07FF-C003: Please pull out the filament on the spool holder",
    134201350: "07FF-C006: Please feed filament into the PTFE tube",
}


def check_printer_ports(printer_ip: str, ports: tuple[int, ...], *, timeout: float = 5.0) -> None:
    failures: list[str] = []
    for port in ports:
        try:
            with socket.create_connection((printer_ip, port), timeout=timeout):
                continue
        except OSError as exc:
            failures.append(f"{printer_ip}:{port} {type(exc).__name__}: {exc}")

    if failures:
        raise PrinterError(
            "Printer LAN services are not reachable",
            suggestion=(
                "Enable LAN Only + Developer Mode, verify the printer IP, and retry. "
                f"Probe result: {'; '.join(failures)}"
            ),
        )


def read_printer_report(
    *,
    printer_ip: str,
    access_code: str,
    serial: str,
    timeout_seconds: float = 8,
) -> dict[str, Any]:
    import paho.mqtt.client as mqtt

    report: dict[str, Any] = {}

    def on_connect(client, userdata, flags, reason_code, properties=None):  # noqa: ANN001, ARG001
        if reason_code == 0 or not getattr(reason_code, "is_failure", True):
            client.subscribe(f"device/{serial}/report")
            client.publish(
                f"device/{serial}/request",
                json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}),
            )

    def on_message(client, userdata, msg):  # noqa: ANN001, ARG001
        doc = json.loads(msg.payload)
        merge_report(report, doc)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"bambu_pipe_report_{uuid.uuid4().hex}",
    )
    client.username_pw_set("bblp", access_code)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(printer_ip, 8883, keepalive=60)
    client.loop_start()
    time.sleep(timeout_seconds)
    client.loop_stop()
    client.disconnect()
    return report


def merge_report(target: dict[str, Any], doc: dict[str, Any]) -> None:
    for key, value in doc.items():
        if isinstance(value, dict):
            current = target.setdefault(key, {})
            current.update(value)
        else:
            target[key] = value


def print_report(report: dict[str, Any]) -> dict[str, Any]:
    value = report.get("print", {})
    return value if isinstance(value, dict) else {}


def ams_report(report: dict[str, Any]) -> dict[str, Any]:
    value = print_report(report).get("ams", {})
    return value if isinstance(value, dict) else {}


def has_filament_block(report: dict[str, Any]) -> bool:
    return print_report(report).get("print_error") == FILAMENT_BLOCK_ERROR_CODE


def has_external_filament_loaded(report: dict[str, Any]) -> bool:
    return print_report(report).get("hw_switch_state") == 1


def filament_block_message(report: dict[str, Any]) -> str:
    current_print_report = print_report(report)
    current_ams_report = ams_report(report)
    return (
        "AMS print is blocked by filament already detected in the external/toolhead path "
        f"(print_error={current_print_report.get('print_error')}, "
        f"ams_status={current_print_report.get('ams_status')}, "
        f"hw_switch_state={current_print_report.get('hw_switch_state')}, "
        f"filam_bak={current_print_report.get('filam_bak')}, "
        f"tray_tar={current_ams_report.get('tray_tar')}, "
        f"tray_now={current_ams_report.get('tray_now')})"
    )


def startup_failure_message(report: dict[str, Any]) -> str:
    current_print_report = print_report(report)
    current_ams_report = ams_report(report)
    print_error = current_print_report.get("print_error")
    error_description = PRINT_ERROR_DESCRIPTIONS.get(print_error, "unknown error")
    return (
        f"Printer failed during startup "
        f"(state={current_print_report.get('gcode_state')}, "
        f"print_error={print_error} [{error_description}], "
        f"mc_print_error_code={current_print_report.get('mc_print_error_code')}, "
        f"ams_status={current_print_report.get('ams_status')}, "
        f"stg_cur={current_print_report.get('stg_cur')}, "
        f"tray_tar={current_ams_report.get('tray_tar')}, "
        f"tray_now={current_ams_report.get('tray_now')}, "
        f"hw_switch_state={current_print_report.get('hw_switch_state')}, "
        f"filam_bak={current_print_report.get('filam_bak')})"
    )
