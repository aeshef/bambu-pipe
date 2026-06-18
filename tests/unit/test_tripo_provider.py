from __future__ import annotations

import httpx
import pytest
from bambu_pipe.models.errors import MeshProviderError
from bambu_pipe.providers.mesh.tripo import _extract_model_url, _raise_for_status


def test_extract_model_url_from_common_tripo_shapes() -> None:
    assert _extract_model_url({"model_url": "https://example.com/model.glb"}) == (
        "https://example.com/model.glb"
    )
    assert _extract_model_url({"result": {"model_url": "https://example.com/result.glb"}}) == (
        "https://example.com/result.glb"
    )
    assert _extract_model_url({"output": {"model": "https://example.com/output.glb"}}) == (
        "https://example.com/output.glb"
    )
    assert _extract_model_url({"output": {"model": {"url": "https://example.com/model.glb"}}}) == (
        "https://example.com/model.glb"
    )
    assert (
        _extract_model_url(
            {"output": {"base_model": {"download_url": "https://example.com/base.glb?token=1"}}}
        )
        == "https://example.com/base.glb?token=1"
    )
    assert (
        _extract_model_url(
            {"output": {"assets": [{"type": "glb", "url": "https://example.com/asset.glb"}]}}
        )
        == "https://example.com/asset.glb"
    )


def test_tripo_rate_limit_error_has_actionable_suggestion() -> None:
    response = httpx.Response(429, json={"message": "quota exceeded"})

    with pytest.raises(MeshProviderError) as exc_info:
        _raise_for_status(response, "create Tripo task")

    message = str(exc_info.value)
    assert "HTTP 429" in message
    assert "rate limit" in message.lower()
    assert "quota exceeded" in message


def test_tripo_auth_error_mentions_api_key() -> None:
    response = httpx.Response(401, json={"error": "invalid token"})

    with pytest.raises(MeshProviderError) as exc_info:
        _raise_for_status(response, "create Tripo task")

    assert "BAMBU_PIPE_TRIPO_API_KEY" in str(exc_info.value)
