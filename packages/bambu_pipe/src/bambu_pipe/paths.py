"""Filesystem path resolution — no hardcoded user or OS-specific paths."""

from __future__ import annotations

import os
from functools import lru_cache
from importlib import resources
from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir

APP_NAME = "bambu-pipe"
ORG_NAME = "bambu-pipe"


def config_dir() -> Path:
    override = os.environ.get("BAMBU_PIPE_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(user_config_dir(APP_NAME, appauthor=ORG_NAME))


def cache_dir() -> Path:
    override = os.environ.get("BAMBU_PIPE_CACHE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(user_cache_dir(APP_NAME, appauthor=ORG_NAME))


def default_config_file() -> Path:
    return config_dir() / "config.env"


def default_staging_dir() -> Path:
    return cache_dir() / "staging"


def default_database_path() -> Path:
    return cache_dir() / "jobs.db"


@lru_cache(maxsize=1)
def bundled_profiles_dir() -> Path | None:
    """Return shipped Orca profile templates, if present in the package."""
    try:
        root = resources.files("bambu_pipe").joinpath("profiles")
        if root.is_dir():
            return Path(str(root))
    except (TypeError, FileNotFoundError):
        pass
    return None


def resolve_profiles_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    env = os.environ.get("BAMBU_PIPE_PROFILES_DIR")
    if env:
        return Path(env).expanduser().resolve()
    bundled = bundled_profiles_dir()
    if bundled is not None:
        return bundled
    return config_dir() / "profiles"


def job_staging_dir(staging_root: Path, job_id: str) -> Path:
    path = staging_root / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path
