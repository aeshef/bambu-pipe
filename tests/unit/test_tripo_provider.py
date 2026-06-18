from __future__ import annotations

from bambu_pipe.providers.mesh.tripo import _extract_model_url


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
