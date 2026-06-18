"""OrcaSlicer binary discovery."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path


def discover_orca_slicer(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        return path if path.is_file() and os.access(path, os.X_OK) else None

    which = shutil.which("orcaslicer")
    if which:
        return Path(which)

    system = platform.system()
    candidates: list[Path] = []

    if system == "Darwin":
        candidates.extend(
            [
                Path("/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"),
                Path.home() / "Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer",
                Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"),
            ]
        )
    elif system == "Linux":
        candidates.extend(
            [
                Path("/usr/bin/orca-slicer"),
                Path("/usr/local/bin/orca-slicer"),
                Path.home() / "Applications/OrcaSlicer.AppImage",
            ]
        )
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates.append(Path(local) / "Programs/OrcaSlicer/orca-slicer.exe")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
