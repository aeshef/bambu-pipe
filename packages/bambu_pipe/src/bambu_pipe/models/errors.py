"""Structured errors for pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BambuPipeError(Exception):
    code: str
    message: str
    recoverable: bool = False
    suggestion: str | None = None

    def __str__(self) -> str:
        base = f"{self.code}: {self.message}"
        if self.suggestion:
            return f"{base} ({self.suggestion})"
        return base


class ConfigError(BambuPipeError):
    def __init__(self, message: str, suggestion: str | None = None) -> None:
        super().__init__("config_error", message, recoverable=False, suggestion=suggestion)


class ValidationFailedError(BambuPipeError):
    def __init__(self, message: str, suggestion: str | None = None) -> None:
        super().__init__("validation_failed", message, recoverable=True, suggestion=suggestion)


class SliceError(BambuPipeError):
    def __init__(self, message: str, suggestion: str | None = None) -> None:
        super().__init__("slice_failed", message, recoverable=True, suggestion=suggestion)


class PrinterError(BambuPipeError):
    def __init__(self, message: str, suggestion: str | None = None) -> None:
        super().__init__("printer_error", message, recoverable=True, suggestion=suggestion)


class JobError(BambuPipeError):
    def __init__(self, message: str) -> None:
        super().__init__("job_error", message, recoverable=False)
