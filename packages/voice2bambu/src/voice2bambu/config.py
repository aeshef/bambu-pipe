"""voice2bambu settings."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class VoiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VOICE2BAMBU_",
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_token: str | None = None
    allowed_user_ids: set[int] = Field(default_factory=set)
    bambu_pipe_api_base_url: str = "http://127.0.0.1:8080/api/v1"
    transcription_api_key: SecretStr | None = None
    transcription_base_url: str = "https://api.openai.com/v1"
    transcription_model: str = "whisper-1"

    @property
    def configured(self) -> bool:
        return bool(
            self.telegram_token
            and self.allowed_user_ids
            and self.transcription_api_key
            and self.transcription_api_key.get_secret_value()
        )

    @property
    def transcription_token(self) -> str:
        if self.transcription_api_key is None:
            return ""
        return self.transcription_api_key.get_secret_value()
