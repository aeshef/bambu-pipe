"""Upload a mesh to the optional local REST adapter."""

from __future__ import annotations

import os
from pathlib import Path

import httpx


def main() -> None:
    api_base_url = os.environ["BAMBU_PIPE_API_BASE_URL"].rstrip("/")
    model_path = Path("model.stl")
    with model_path.open("rb") as handle:
        response = httpx.post(
            f"{api_base_url}/jobs/upload",
            params={"material": "PETG", "auto_approve": False},
            files={"file": (model_path.name, handle, "model/stl")},
            timeout=60,
        )
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    main()
