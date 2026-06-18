"""Mesh provider factory."""

from __future__ import annotations

from bambu_pipe.config import Settings
from bambu_pipe.models.errors import ConfigError
from bambu_pipe.providers.mesh.base import MeshProvider


def create_mesh_provider(settings: Settings) -> MeshProvider:
    provider = settings.mesh_provider.strip().lower()
    if provider == "tripo":
        api_key = settings.secret(settings.tripo_api_key)
        if not api_key:
            raise ConfigError(
                "Tripo provider selected but BAMBU_PIPE_TRIPO_API_KEY is not set",
                suggestion="Set BAMBU_PIPE_TRIPO_API_KEY or use mesh_only mode.",
            )
        try:
            from bambu_pipe.providers.mesh.tripo import TripoMeshProvider
        except ImportError as exc:
            raise ConfigError(
                "Tripo provider dependencies are not installed",
                suggestion='Install bambu-pipe with `pip install "bambu-pipe[tripo]"`.',
            ) from exc
        return TripoMeshProvider(api_key=api_key, base_url=settings.tripo_base_url)
    raise ConfigError(
        f"Unknown mesh provider: {settings.mesh_provider}",
        suggestion="Configured providers: tripo",
    )
