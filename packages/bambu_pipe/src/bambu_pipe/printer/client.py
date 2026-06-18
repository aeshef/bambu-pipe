"""Bambu Lab printer client."""

from __future__ import annotations

import asyncio
import ftplib
import time
from pathlib import Path

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import ConfigError, PrinterError
from bambu_pipe.printer.ftp import upload_ftps
from bambu_pipe.printer.mqtt import start_print_mqtt
from bambu_pipe.printer.status import (
    ams_report as extract_ams_report,
)
from bambu_pipe.printer.status import (
    check_printer_ports,
    filament_block_message,
    has_external_filament_loaded,
    has_filament_block,
    print_report,
    read_printer_report,
)

_PRINTER_RETRY_ATTEMPTS = 4
_PRINTER_RETRY_DELAY_SECONDS = 2.0


def _with_printer_retries(operation_name: str, func):  # noqa: ANN001, ANN202
    last_error: BaseException | None = None
    for attempt in range(1, _PRINTER_RETRY_ATTEMPTS + 1):
        try:
            return func()
        except (OSError, TimeoutError, ftplib.Error) as exc:
            last_error = exc
            if attempt == _PRINTER_RETRY_ATTEMPTS:
                break
            time.sleep(_PRINTER_RETRY_DELAY_SECONDS)
    raise PrinterError(
        f"{operation_name} failed after {_PRINTER_RETRY_ATTEMPTS} attempts: {last_error}",
        suggestion="Check LAN Only + Developer Mode and retry when ports 990/8883 are reachable",
    )


def _prepare_ams_print(
    *,
    printer_ip: str,
    access_code: str,
    serial: str,
    use_ams: bool,
) -> None:
    if not use_ams:
        return

    report = read_printer_report(
        printer_ip=printer_ip,
        access_code=access_code,
        serial=serial,
    )
    if not has_filament_block(report):
        return
    raise PrinterError(
        filament_block_message(report),
        suggestion=(
            "AMS mode requires an empty toolhead/external filament path. "
            "Either unload the currently loaded filament first or set "
            "BAMBU_PIPE_USE_AMS=false to print with the already loaded filament."
        ),
    )


def _prepare_external_print(
    *,
    printer_ip: str,
    access_code: str,
    serial: str,
    use_ams: bool,
) -> None:
    if use_ams:
        return

    report = read_printer_report(
        printer_ip=printer_ip,
        access_code=access_code,
        serial=serial,
    )
    if has_external_filament_loaded(report):
        return

    raise PrinterError(
        "External/manual print mode requires filament already fed into the PTFE path",
        suggestion=(
            "Feed filament into the external PTFE until the printer detects it, "
            "or set BAMBU_PIPE_USE_AMS=true and choose BAMBU_PIPE_AMS_SLOT."
        ),
    )


def upload_ftps_with_retries(printer_ip: str, access_code: str, local_path: Path) -> str:
    return _with_printer_retries(
        "FTPS upload",
        lambda: upload_ftps(printer_ip, access_code, local_path),
    )


def _start_print_mqtt_with_retries(
    *,
    printer_ip: str,
    access_code: str,
    serial: str,
    filename: str,
    use_ams: bool,
    ams_slot: int,
) -> None:
    return _with_printer_retries(
        "MQTT start_print",
        lambda: start_print_mqtt(
            printer_ip=printer_ip,
            access_code=access_code,
            serial=serial,
            filename=filename,
            use_ams=use_ams,
            ams_slot=ams_slot,
        ),
    )


def _get_printer_status(settings: Settings) -> dict[str, object]:
    if not settings.printer_configured:
        raise ConfigError("Printer is not configured")

    check_printer_ports(settings.printer_ip, (8883,))
    report = read_printer_report(
        printer_ip=settings.printer_ip,
        access_code=settings.secret(settings.printer_access_code),
        serial=settings.printer_serial,
    )
    if not report:
        raise PrinterError(
            "Connected to MQTT but did not receive a printer report",
            suggestion="Check that the serial number and access code match the printer.",
        )
    current_print_report = print_report(report)
    current_ams_report = extract_ams_report(report)
    return {
        "state": current_print_report.get("gcode_state"),
        "print_error": current_print_report.get("print_error"),
        "mc_print_error_code": current_print_report.get("mc_print_error_code"),
        "ams_status": current_print_report.get("ams_status"),
        "tray_now": current_ams_report.get("tray_now"),
        "tray_tar": current_ams_report.get("tray_tar"),
        "hw_switch_state": current_print_report.get("hw_switch_state"),
    }


class BambuPrinterClient:
    async def ensure_reachable(self, settings: Settings) -> None:
        if not settings.printer_configured:
            raise ConfigError(
                "Printer is not configured",
                suggestion="Set BAMBU_PIPE_PRINTER_IP, PRINTER_SERIAL, PRINTER_ACCESS_CODE",
            )
        await asyncio.to_thread(check_printer_ports, settings.printer_ip, (8883, 990))

    async def upload(self, settings: Settings, local_path: Path) -> str:
        if not settings.printer_configured:
            raise ConfigError(
                "Printer is not configured",
                suggestion="Set BAMBU_PIPE_PRINTER_IP, PRINTER_SERIAL, PRINTER_ACCESS_CODE",
            )
        await asyncio.to_thread(check_printer_ports, settings.printer_ip, (990,))
        return await asyncio.to_thread(
            upload_ftps_with_retries,
            settings.printer_ip,
            settings.secret(settings.printer_access_code),
            local_path,
        )

    async def start_print(self, settings: Settings, filename: str) -> None:
        if not settings.printer_configured:
            raise ConfigError("Printer is not configured")
        await asyncio.to_thread(check_printer_ports, settings.printer_ip, (8883,))
        await asyncio.to_thread(
            _prepare_ams_print,
            printer_ip=settings.printer_ip,
            access_code=settings.secret(settings.printer_access_code),
            serial=settings.printer_serial,
            use_ams=settings.use_ams,
        )
        await asyncio.to_thread(
            _prepare_external_print,
            printer_ip=settings.printer_ip,
            access_code=settings.secret(settings.printer_access_code),
            serial=settings.printer_serial,
            use_ams=settings.use_ams,
        )
        await asyncio.to_thread(
            _start_print_mqtt_with_retries,
            printer_ip=settings.printer_ip,
            access_code=settings.secret(settings.printer_access_code),
            serial=settings.printer_serial,
            filename=filename,
            use_ams=settings.use_ams,
            ams_slot=settings.ams_slot,
        )

    async def upload_and_print(self, settings: Settings, local_path: Path) -> str:
        filename = await self.upload(settings, local_path)
        await self.start_print(settings, filename)
        return filename

    async def status(self, settings: Settings) -> dict[str, object]:
        return await asyncio.to_thread(_get_printer_status, settings)
