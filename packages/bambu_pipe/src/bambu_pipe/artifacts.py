"""Job artifact manifest and preview helpers."""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

from bambu_pipe.models.job import PrintJob


def write_artifact_manifest(job: PrintJob, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "artifact-manifest.json"
    manifest_path.write_text(
        json.dumps(_manifest_payload(job), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    job.artifacts.artifact_manifest_path = str(manifest_path)
    return manifest_path


def write_preview_artifacts(job: PrintJob, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = _copy_preview_image(job, output_dir)
    if image_path is not None:
        job.artifacts.preview_image_path = str(image_path)

    html_path = output_dir / "preview.html"
    html_path.write_text(_preview_html(job), encoding="utf-8")
    job.artifacts.preview_html_path = str(html_path)
    write_artifact_manifest(job, output_dir)


def _manifest_payload(job: PrintJob) -> dict[str, Any]:
    validation = job.artifacts.validation
    return {
        "job_id": job.id,
        "mode": job.mode,
        "stage": job.stage,
        "prompt": job.prompt or None,
        "quality": job.quality,
        "material": job.material,
        "model_path": job.artifacts.model_path or job.model_path,
        "sliced_path": job.artifacts.sliced_path,
        "thumbnail_path": job.artifacts.thumbnail_path,
        "preview_html_path": job.artifacts.preview_html_path,
        "preview_image_path": job.artifacts.preview_image_path,
        "provider_payload_paths": job.artifacts.provider_payload_paths,
        "estimated_print_time": job.artifacts.estimated_print_time,
        "estimated_filament_g": job.artifacts.estimated_filament_g,
        "model_dimensions_mm": job.artifacts.model_dimensions_mm,
        "confidence_score": validation.score if validation else None,
        "validation_passed": validation.passed if validation else None,
        "validation_checks": [check.model_dump() for check in validation.checks]
        if validation
        else [],
    }


def _copy_preview_image(job: PrintJob, output_dir: Path) -> Path | None:
    if not job.artifacts.thumbnail_path:
        return None
    source = Path(job.artifacts.thumbnail_path)
    if not source.is_file():
        return None
    destination = output_dir / f"preview{source.suffix or '.png'}"
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination


def _preview_html(job: PrintJob) -> str:
    validation = job.artifacts.validation
    confidence = (
        f"{validation.score}%" if validation and validation.score is not None else "unknown"
    )
    rows = [
        ("Job", job.id),
        ("Stage", job.stage.value),
        ("Mode", job.mode),
        ("Quality", job.quality),
        ("Material", job.material),
        ("Dimensions", _dimensions_text(job.artifacts.model_dimensions_mm)),
        ("Estimated time", job.artifacts.estimated_print_time or "unknown"),
        ("Estimated filament", _filament_text(job.artifacts.estimated_filament_g)),
        ("Confidence", confidence),
        ("Model", job.artifacts.model_path or job.model_path or "-"),
        ("Slice", job.artifacts.sliced_path or "-"),
    ]
    checks = validation.checks if validation else []
    image_name = (
        html.escape(Path(job.artifacts.preview_image_path).name)
        if job.artifacts.preview_image_path
        else ""
    )
    image = (
        f'<img class="preview" src="{image_name}" alt="Preview">'
        if job.artifacts.preview_image_path
        else '<div class="placeholder">No slicer thumbnail available</div>'
    )
    rows_html = "\n".join(
        f"<tr><th>{html.escape(name)}</th><td>{html.escape(str(value))}</td></tr>"
        for name, value in rows
    )
    checks_html = "\n".join(
        "<tr>"
        f"<td>{html.escape(check.name)}</td>"
        f"<td>{'pass' if check.passed else 'fail'}</td>"
        f"<td>{html.escape(check.severity)}</td>"
        f"<td>{html.escape(check.message)}</td>"
        "</tr>"
        for check in checks
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>bambu-pipe preview {html.escape(job.id)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 2rem;
      color: #17202a;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(280px, 420px) 1fr;
      gap: 2rem;
      align-items: start;
    }}
    .preview {{
      max-width: 100%;
      border-radius: 16px;
      border: 1px solid #dde4ea;
      background: #f8fafc;
    }}
    .placeholder {{
      padding: 4rem 2rem;
      border: 1px dashed #aab7c4;
      border-radius: 16px;
      color: #52616f;
      text-align: center;
    }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{
      border-bottom: 1px solid #e5eaf0;
      padding: 0.55rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{ width: 11rem; color: #52616f; }}
    h1, h2 {{ margin-top: 0; }}
  </style>
</head>
<body>
  <h1>bambu-pipe print preview</h1>
  <div class="layout">
    <section>{image}</section>
    <section>
      <h2>Plan</h2>
      <table>{rows_html}</table>
      <h2>Validation</h2>
      <table>
        <tr><th>Check</th><th>Status</th><th>Severity</th><th>Message</th></tr>
        {checks_html}
      </table>
    </section>
  </div>
</body>
</html>
"""


def _dimensions_text(dimensions: list[float] | None) -> str:
    if not dimensions:
        return "unknown"
    return " x ".join(f"{value:.1f} mm" for value in dimensions)


def _filament_text(value: float | None) -> str:
    return f"{value:.1f} g" if value is not None else "unknown"
