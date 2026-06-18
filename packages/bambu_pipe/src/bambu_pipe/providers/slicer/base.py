"""Slicer result models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SliceResult:
    output_path: Path
    estimated_print_time: str | None = None
    estimated_filament_g: float | None = None
    thumbnail_path: Path | None = None
