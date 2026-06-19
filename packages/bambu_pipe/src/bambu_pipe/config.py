"""Application configuration via environment variables and optional config file."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from bambu_pipe.paths import (
    default_config_file,
    default_database_path,
    default_staging_dir,
    resolve_profiles_dir,
)


class Settings(BaseSettings):
    """All settings are loaded from environment variables prefixed with BAMBU_PIPE_."""

    model_config = SettingsConfigDict(
        env_prefix="BAMBU_PIPE_",
        env_file=(".env", str(default_config_file())),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Printer
    printer_ip: str | None = None
    printer_serial: str | None = None
    printer_access_code: SecretStr | None = None
    printer_model: Literal["A1"] = "A1"
    use_ams: bool = False
    ams_slot: int = Field(default=1, ge=1, le=4)

    # Slicer
    slicer_mode: Literal["local"] = "local"
    slicer_binary: Path | None = None
    profiles_dir: Path | None = None
    quality: Literal["draft", "standard", "fine"] = "standard"
    material: str = "PLA"

    # Pipeline behaviour
    auto_approve: bool = False
    max_upload_mb: int = Field(default=64, ge=1)
    max_estimated_print_minutes: int | None = Field(default=None, ge=1)
    staging_dir: Path = Field(default_factory=default_staging_dir)
    database_path: Path = Field(default_factory=default_database_path)

    # Optional local REST adapter guard
    api_token: SecretStr | None = None

    # Build volume for A1 (mm) — used by validation; scoring hooks use the same constants
    bed_width_mm: float = 256.0
    bed_depth_mm: float = 256.0
    bed_height_mm: float = 256.0

    # Text-to-3D provider
    mesh_provider: str = "tripo"
    tripo_api_key: SecretStr | None = None
    tripo_base_url: str = "https://api.tripo3d.ai/v2/openapi"
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    @field_validator("staging_dir", "database_path", mode="before")
    @classmethod
    def _expand_path(cls, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    @property
    def resolved_profiles_dir(self) -> Path:
        return resolve_profiles_dir(self.profiles_dir)

    @property
    def printer_configured(self) -> bool:
        return bool(
            self.printer_ip
            and self.printer_serial
            and self.printer_access_code
            and self.printer_access_code.get_secret_value()
        )

    def ensure_runtime_dirs(self) -> None:
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def secret(self, field: SecretStr | None) -> str | None:
        if field is None:
            return None
        value = field.get_secret_value()
        return value or None


def load_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
