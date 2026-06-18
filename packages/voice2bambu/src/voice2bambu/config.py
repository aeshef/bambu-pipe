"""voice2bambu settings."""

from __future__ import annotations

import os

from pydantic import Field, SecretStr, model_validator
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
    bambu_pipe_api_base_url: str | None = None
    transcription_api_key: SecretStr | None = None
    transcription_base_url: str = "https://api.openai.com/v1"
    transcription_model: str = "whisper-1"
    transcription_language: str | None = None

    @model_validator(mode="after")
    def _apply_legacy_asr_aliases(self) -> VoiceSettings:
        """Accept common ASR env names without making them the public contract."""
        if self.transcription_api_key is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                self.transcription_api_key = SecretStr(api_key)

        if self.transcription_model == "whisper-1":
            model = os.getenv("ASR_MODEL")
            if model:
                self.transcription_model = model

        if self.transcription_base_url == "https://api.openai.com/v1":
            base_url = os.getenv("ASR_BASE_URL")
            if base_url:
                self.transcription_base_url = base_url

        if self.transcription_language is None:
            language = os.getenv("ASR_LANGUAGE")
            if language:
                self.transcription_language = language

        return self

    @property
    def configured(self) -> bool:
        return bool(
            self.telegram_token
            and self.allowed_user_ids
            and self.bambu_pipe_api_base_url
            and self.transcription_api_key
            and self.transcription_api_key.get_secret_value()
        )

    @property
    def transcription_token(self) -> str:
        if self.transcription_api_key is None:
            return ""
        return self.transcription_api_key.get_secret_value()
