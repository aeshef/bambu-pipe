"""Text-to-3D mesh provider contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class MeshGenerationRequest:
    prompt: str
    output_dir: Path
    target_format: str = "stl"


@dataclass(frozen=True)
class MeshGenerationResult:
    model_path: Path
    provider: str
    raw_prompt: str
    raw_payload_paths: tuple[Path, ...] = ()


class MeshProvider(Protocol):
    async def generate(self, request: MeshGenerationRequest) -> MeshGenerationResult: ...
