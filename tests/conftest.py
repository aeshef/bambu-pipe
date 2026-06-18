from __future__ import annotations

from pathlib import Path

import pytest
from bambu_pipe.config import Settings


@pytest.fixture
def tmp_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("BAMBU_PIPE_STAGING_DIR", str(tmp_path / "staging"))
    monkeypatch.setenv("BAMBU_PIPE_DATABASE_PATH", str(tmp_path / "jobs.db"))
    monkeypatch.setenv(
        "BAMBU_PIPE_PROFILES_DIR",
        str(Path(__file__).resolve().parents[1] / "fixtures" / "profiles"),
    )
    monkeypatch.setenv("BAMBU_PIPE_PRINTER_IP", "192.0.2.10")
    monkeypatch.setenv("BAMBU_PIPE_PRINTER_SERIAL", "TESTSERIAL")
    monkeypatch.setenv("BAMBU_PIPE_PRINTER_ACCESS_CODE", "testcode")
    return Settings()
