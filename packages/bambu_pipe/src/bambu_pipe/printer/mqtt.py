"""MQTT print-start transport for Bambu LAN printers."""

from __future__ import annotations

import json
import ssl
import time
import uuid
from typing import Any

from bambu_pipe.models.errors import PrinterError
from bambu_pipe.printer.payload import build_project_file_payload
from bambu_pipe.printer.status import (
    EXTERNAL_FILAMENT_MISSING_ERROR_CODE,
    filament_block_message,
    has_filament_block,
    merge_report,
    print_report,
    startup_failure_message,
)

START_HEALTHCHECK_SECONDS = 240


def publish_and_monitor_print_start(
    *,
    printer_ip: str,
    access_code: str,
    serial: str,
    payload: dict[str, object],
    use_ams: bool,
) -> None:
    import paho.mqtt.client as mqtt

    command_topic = f"device/{serial}/request"
    report_topic = f"device/{serial}/report"
    connected = False
    published = False
    connect_error: str | None = None
    latest_report: dict[str, Any] = {}
    first_error_report: dict[str, Any] | None = None
    first_failed_report: dict[str, Any] | None = None
    saw_running = False
    stable_running_since: float | None = None

    def on_connect(client, userdata, flags, reason_code, properties=None):  # noqa: ANN001, ARG001
        nonlocal connected, published, connect_error
        if reason_code != 0 and getattr(reason_code, "is_failure", False):
            connect_error = f"MQTT connect failed: rc={reason_code}"
            return
        connected = True
        client.subscribe(report_topic)
        client.publish(
            command_topic,
            json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}),
        )
        client.publish(command_topic, json.dumps(payload))
        published = True

    def on_message(client, userdata, msg):  # noqa: ANN001, ARG001
        nonlocal first_error_report, first_failed_report, saw_running, stable_running_since
        doc = json.loads(msg.payload)
        merge_report(latest_report, doc)
        current_print_report = print_report(latest_report)
        print_error = current_print_report.get("print_error")
        state = current_print_report.get("gcode_state")
        if print_error not in (None, 0) and first_error_report is None:
            first_error_report = json.loads(json.dumps(latest_report))
        if state == "FAILED" and print_error not in (None, 0) and first_failed_report is None:
            first_failed_report = json.loads(json.dumps(latest_report))
        if state == "RUNNING":
            saw_running = True
            stable_running_since = stable_running_since or time.time()
        else:
            stable_running_since = None

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"bambu_pipe_start_{uuid.uuid4().hex}",
    )
    client.username_pw_set("bblp", access_code)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(printer_ip, 8883, keepalive=60)
    client.loop_start()

    deadline = time.time() + START_HEALTHCHECK_SECONDS
    while time.time() < deadline:
        if connect_error:
            client.loop_stop()
            client.disconnect()
            raise PrinterError(connect_error, suggestion="Enable Developer Mode on the printer")
        if connected and published:
            if first_error_report is not None:
                client.loop_stop()
                client.disconnect()
                print_error = print_report(first_error_report).get("print_error")
                if print_error == EXTERNAL_FILAMENT_MISSING_ERROR_CODE:
                    raise PrinterError(
                        startup_failure_message(first_error_report),
                        suggestion=(
                            "The print was started in external/manual mode but filament was "
                            "not fed into the PTFE path. Use AMS mode or feed external filament."
                        ),
                    )
                raise PrinterError(
                    startup_failure_message(first_error_report),
                    suggestion="Printer reported a transient startup error before it was cleared.",
                )
            if first_failed_report is not None:
                client.loop_stop()
                client.disconnect()
                raise PrinterError(
                    startup_failure_message(first_failed_report),
                    suggestion="Printer entered FAILED during startup monitoring.",
                )
            if use_ams and has_filament_block(latest_report):
                client.loop_stop()
                client.disconnect()
                raise PrinterError(
                    filament_block_message(latest_report),
                    suggestion=(
                        "AMS load failed after start. The printer still sees filament in "
                        "the external/toolhead path; unload it before retrying."
                    ),
                )
            if stable_running_since and time.time() - stable_running_since >= 120:
                client.loop_stop()
                client.disconnect()
                return
        time.sleep(0.2)

    client.loop_stop()
    client.disconnect()

    if connect_error:
        raise PrinterError(connect_error, suggestion="Enable Developer Mode on the printer")
    if not published:
        raise PrinterError("Timed out waiting for MQTT connection")
    if not saw_running:
        raise PrinterError(
            "Printer did not report RUNNING after project_file command",
            suggestion=f"Last report: {print_report(latest_report)}",
        )


def start_print_mqtt(
    *,
    printer_ip: str,
    access_code: str,
    serial: str,
    filename: str,
    use_ams: bool,
    ams_slot: int,
) -> None:
    payload = build_project_file_payload(
        filename=filename,
        use_ams=use_ams,
        physical_ams_slot=ams_slot,
    )
    publish_and_monitor_print_start(
        printer_ip=printer_ip,
        access_code=access_code,
        serial=serial,
        payload=payload,
        use_ams=use_ams,
    )
