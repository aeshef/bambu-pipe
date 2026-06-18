from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "voice2bambu" / "src"))

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
