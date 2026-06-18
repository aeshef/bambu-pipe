"""Text-to-3D generation stage."""

from __future__ import annotations

from pathlib import Path

import trimesh

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import JobError
from bambu_pipe.models.job import JobStage, PrintJob
from bambu_pipe.paths import job_staging_dir
from bambu_pipe.providers.mesh.base import MeshGenerationRequest, MeshProvider
from bambu_pipe.providers.mesh.factory import create_mesh_provider


class DefaultGenerationStage:
    def __init__(self, mesh_provider: MeshProvider | None = None) -> None:
        self._mesh_provider = mesh_provider

    async def run(self, job: PrintJob, settings: Settings) -> None:
        if not job.prompt:
            raise JobError("Generation requires a prompt")

        if job.stage != JobStage.GENERATING:
            job.advance(JobStage.GENERATING)

        output_dir = job_staging_dir(settings.staging_dir, job.id)
        provider = self._mesh_provider or create_mesh_provider(settings)
        result = await provider.generate(
            MeshGenerationRequest(prompt=job.prompt, output_dir=output_dir)
        )
        model_path = _ensure_slicer_mesh(result.model_path)
        job.model_path = str(model_path)
        job.artifacts.model_path = str(model_path)
        job.artifacts.model_format = Path(model_path).suffix.lower().lstrip(".")
        job.advance(JobStage.AWAITING_MODEL_APPROVAL)


def _ensure_slicer_mesh(model_path: Path) -> Path:
    if model_path.suffix.lower() not in {".glb", ".gltf"}:
        return model_path

    loaded = trimesh.load(model_path, force="scene")
    if isinstance(loaded, trimesh.Scene):
        mesh = loaded.dump(concatenate=True)
    else:
        mesh = loaded

    destination = model_path.with_suffix(".stl")
    mesh.export(destination)
    return destination
