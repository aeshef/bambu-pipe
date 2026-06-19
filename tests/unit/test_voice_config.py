from __future__ import annotations

from voice2bambu.bot import _api_base_url, _transcription_data
from voice2bambu.config import VoiceSettings


def test_voice_settings_accept_legacy_asr_aliases(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("ASR_MODEL", "whisper-small-russian")
    monkeypatch.setenv("ASR_LANGUAGE", "ru,en")
    monkeypatch.setenv("ASR_BASE_URL", "https://example.com/v1")

    settings = VoiceSettings()

    assert settings.transcription_token == "test-key"
    assert settings.transcription_model == "whisper-small-russian"
    assert settings.transcription_language == "ru,en"
    assert settings.transcription_base_url == "https://example.com/v1"


def test_transcription_data_uses_first_language_hint() -> None:
    settings = VoiceSettings(
        transcription_model="whisper-small-russian",
        transcription_language="ru,en",
    )

    assert _transcription_data(settings) == {
        "model": "whisper-small-russian",
        "language": "ru",
    }


def test_api_base_url_trims_trailing_slash() -> None:
    settings = VoiceSettings(bambu_pipe_api_base_url="http://printer-box:8080/api/v1/")

    assert _api_base_url(settings) == "http://printer-box:8080/api/v1"
