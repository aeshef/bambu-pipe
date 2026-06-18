"""Tripo-compatible text-to-3D provider."""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urljoin

import httpx

from bambu_pipe.models.errors import BambuPipeError
from bambu_pipe.providers.mesh.base import MeshGenerationRequest, MeshGenerationResult


class TripoMeshProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        poll_interval_seconds: float = 5.0,
        timeout_seconds: float = 900.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/") + "/"
        self._poll_interval_seconds = poll_interval_seconds
        self._timeout_seconds = timeout_seconds

    async def generate(self, request: MeshGenerationRequest) -> MeshGenerationResult:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(headers=headers, timeout=60) as client:
            task_id = await self._create_task(client, request.prompt)
            model_url = await self._wait_for_model_url(client, task_id)
            model_path = await self._download_model(client, model_url, request.output_dir)
        return MeshGenerationResult(
            model_path=model_path,
            provider="tripo",
            raw_prompt=request.prompt,
        )

    async def _create_task(self, client: httpx.AsyncClient, prompt: str) -> str:
        response = await client.post(
            urljoin(self._base_url, "task"),
            json={"type": "text_to_model", "prompt": prompt},
        )
        response.raise_for_status()
        payload = response.json()
        task_id = payload.get("data", {}).get("task_id") or payload.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise BambuPipeError(f"Tripo response did not contain task_id: {payload}")
        return task_id

    async def _wait_for_model_url(self, client: httpx.AsyncClient, task_id: str) -> str:
        deadline = asyncio.get_running_loop().time() + self._timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            response = await client.get(urljoin(self._base_url, f"task/{task_id}"))
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", payload)
            status = str(data.get("status", "")).lower()
            if status in {"success", "succeeded", "completed"}:
                model_url = _extract_model_url(data)
                if model_url:
                    return model_url
                raise BambuPipeError(f"Tripo task completed without model URL: {payload}")
            if status in {"failed", "error", "cancelled"}:
                raise BambuPipeError(f"Tripo task failed: {payload}")
            await asyncio.sleep(self._poll_interval_seconds)
        raise BambuPipeError(f"Tripo task timed out: {task_id}")

    async def _download_model(
        self,
        client: httpx.AsyncClient,
        model_url: str,
        output_dir: Path,
    ) -> Path:
        response = await client.get(model_url)
        response.raise_for_status()
        suffix = Path(model_url.split("?", 1)[0]).suffix or ".glb"
        destination = output_dir / f"generated{suffix}"
        destination.write_bytes(response.content)
        return destination


def _extract_model_url(data: dict[str, object]) -> str | None:
    candidates = [
        data.get("model_url"),
        data.get("output_model_url"),
        data.get("result", {}).get("model_url") if isinstance(data.get("result"), dict) else None,
        data.get("output", {}).get("model") if isinstance(data.get("output"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return candidate
    return None
