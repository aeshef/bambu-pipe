"""Tripo-compatible text-to-3D provider."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin

import httpx

from bambu_pipe.models.errors import MeshProviderError
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
        try:
            async with httpx.AsyncClient(headers=headers, timeout=60) as client:
                payload_paths: list[Path] = []
                task_id = await self._create_task(
                    client,
                    request.prompt,
                    request.output_dir,
                    payload_paths,
                )
                model_url = await self._wait_for_model_url(
                    client,
                    task_id,
                    request.output_dir,
                    payload_paths,
                )
                model_path = await self._download_model(client, model_url, request.output_dir)
        except httpx.TimeoutException as exc:
            raise MeshProviderError(
                "Tripo request timed out",
                suggestion="Retry later or increase provider timeout settings.",
            ) from exc
        except httpx.RequestError as exc:
            raise MeshProviderError(
                f"Tripo network request failed: {exc}",
                suggestion="Check network access and BAMBU_PIPE_TRIPO_BASE_URL.",
            ) from exc
        return MeshGenerationResult(
            model_path=model_path,
            provider="tripo",
            raw_prompt=request.prompt,
            raw_payload_paths=tuple(payload_paths),
        )

    async def _create_task(
        self,
        client: httpx.AsyncClient,
        prompt: str,
        output_dir: Path,
        payload_paths: list[Path],
    ) -> str:
        response = await client.post(
            urljoin(self._base_url, "task"),
            json={"type": "text_to_model", "prompt": prompt},
        )
        _raise_for_status(response, "create Tripo task")
        payload = _json_payload(response, "create Tripo task")
        payload_paths.append(_write_payload(output_dir, "tripo-create-task", payload))
        task_id = payload.get("data", {}).get("task_id") or payload.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise MeshProviderError(
                "Tripo response did not contain task_id",
                suggestion=f"Provider response: {payload}",
            )
        return task_id

    async def _wait_for_model_url(
        self,
        client: httpx.AsyncClient,
        task_id: str,
        output_dir: Path,
        payload_paths: list[Path],
    ) -> str:
        deadline = asyncio.get_running_loop().time() + self._timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            response = await client.get(urljoin(self._base_url, f"task/{task_id}"))
            _raise_for_status(response, "poll Tripo task")
            payload = _json_payload(response, "poll Tripo task")
            poll_path = _write_payload(output_dir, "tripo-poll-latest", payload)
            if poll_path not in payload_paths:
                payload_paths.append(poll_path)
            data = payload.get("data", payload)
            if not isinstance(data, dict):
                raise MeshProviderError(
                    "Tripo task response did not contain an object payload",
                    suggestion=f"Provider response: {payload}",
                )
            status = str(data.get("status", "")).lower()
            if status in {"success", "succeeded", "completed"}:
                model_url = _extract_model_url(data)
                if model_url:
                    return model_url
                raise MeshProviderError(
                    "Tripo task completed without a downloadable model URL",
                    suggestion="Check provider dashboard/logs and retry with a simpler prompt.",
                )
            if status in {"failed", "error", "cancelled"}:
                raise MeshProviderError(
                    f"Tripo task ended with status `{status}`",
                    suggestion=_failure_detail(data) or "Retry with a simpler printable prompt.",
                )
            await asyncio.sleep(self._poll_interval_seconds)
        raise MeshProviderError(
            f"Tripo task timed out after {self._timeout_seconds:.0f}s: {task_id}",
            suggestion="Check provider status, credits, and task dashboard before retrying.",
        )

    async def _download_model(
        self,
        client: httpx.AsyncClient,
        model_url: str,
        output_dir: Path,
    ) -> Path:
        response = await client.get(model_url)
        _raise_for_status(response, "download Tripo model")
        if not response.content:
            raise MeshProviderError(
                "Tripo model download returned an empty file",
                suggestion="Retry the task or inspect the provider output URL.",
            )
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
        data.get("output", {}).get("base_model") if isinstance(data.get("output"), dict) else None,
        data.get("output", {}).get("pbr_model") if isinstance(data.get("output"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return candidate
        if isinstance(candidate, dict):
            nested = _extract_url_from_value(candidate)
            if nested:
                return nested
    for key in ("output", "result"):
        value = data.get(key)
        nested = _extract_url_from_value(value)
        if nested:
            return nested
    return None


def _extract_url_from_value(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.split("?", 1)[0].lower()
        if cleaned.startswith(("http://", "https://")) and cleaned.endswith(
            (".glb", ".gltf", ".stl", ".obj", ".fbx", ".zip")
        ):
            return value
        return None
    if isinstance(value, dict):
        for key in ("url", "model", "model_url", "download_url", "base_model", "pbr_model"):
            nested = _extract_url_from_value(value.get(key))
            if nested:
                return nested
        for nested_value in value.values():
            nested = _extract_url_from_value(nested_value)
            if nested:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _extract_url_from_value(item)
            if nested:
                return nested
    return None


def _json_payload(response: httpx.Response, operation: str) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise MeshProviderError(
            f"Tripo {operation} returned non-JSON response",
            suggestion=f"HTTP {response.status_code}: {response.text[:300]}",
        ) from exc
    if not isinstance(payload, dict):
        raise MeshProviderError(
            f"Tripo {operation} returned unexpected JSON type",
            suggestion=f"Provider response: {payload}",
        )
    return payload


def _write_payload(output_dir: Path, name: str, payload: dict[str, object]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _raise_for_status(response: httpx.Response, operation: str) -> None:
    if response.status_code < 400:
        return

    detail = _error_detail(response)
    if response.status_code in {401, 403}:
        suggestion = "Check BAMBU_PIPE_TRIPO_API_KEY and provider account access."
    elif response.status_code == 429:
        suggestion = "Tripo rate limit or quota reached. Wait, reduce retries, or check credits."
    elif 500 <= response.status_code:
        suggestion = "Provider server error. Retry later or check Tripo status."
    else:
        suggestion = "Check provider request settings and prompt payload."
    if detail:
        suggestion = f"{suggestion} Provider detail: {detail}"
    raise MeshProviderError(
        f"Tripo {operation} failed with HTTP {response.status_code}",
        suggestion=suggestion,
    )


def _error_detail(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300] or None
    if isinstance(payload, dict):
        return _failure_detail(payload)
    return str(payload)[:300]


def _failure_detail(data: dict[str, object]) -> str | None:
    for key in ("message", "error", "detail", "reason"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            nested = _failure_detail(value)
            if nested:
                return nested
    return None
