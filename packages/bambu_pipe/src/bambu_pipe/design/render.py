"""Headless CPU rendering: identical geometry in four labeled views."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path


def _rasterize(mesh, elevation: float, azimuth: float, width: int = 840, height: int = 600):  # noqa: ANN001
    """Orthographic projection with per-pixel depth, including holes and hidden faces."""
    import numpy as np

    elev, azim = np.deg2rad([elevation, azimuth])
    eye = np.array([np.cos(elev) * np.cos(azim), np.cos(elev) * np.sin(azim), np.sin(elev)])
    right = np.array([-np.sin(azim), np.cos(azim), 0.0])
    up = np.cross(eye, right)
    projected = mesh.triangles @ np.column_stack([right, up, eye])
    low = projected[:, :, :2].min(axis=(0, 1))
    high = projected[:, :, :2].max(axis=(0, 1))
    center = (low + high) / 2
    view_height = max(high[1] - low[1], (high[0] - low[0]) * height / width, 1e-6) * 1.2
    span = np.array([view_height * width / height, view_height])
    low, high = center - span / 2, center + span / 2
    pixels = (projected[:, :, :2] - low) / span * [width, height] - 0.5
    light = np.array([0.3, -0.5, 0.8])
    light /= np.linalg.norm(light)
    intensity = 0.4 + 0.6 * np.clip(mesh.face_normals @ light, 0, 1)
    colors = (intensity[:, None] * [0.25, 0.65, 0.85] * 255).astype(np.uint8)
    image = np.zeros((height, width, 4), dtype=np.uint8)
    depth = np.full((height, width), -np.inf)
    for triangle, coordinates, color in zip(projected, pixels, colors, strict=True):
        (x0, y0), (x1, y1), (x2, y2) = coordinates
        denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denominator) < 1e-12:
            continue  # Edge-on faces have no projected area.
        xmin, ymin = np.maximum(np.ceil(coordinates.min(axis=0)).astype(int), 0)
        xmax, ymax = np.minimum(
            np.floor(coordinates.max(axis=0)).astype(int), [width - 1, height - 1]
        )
        if xmax < xmin or ymax < ymin:
            continue
        x, y = np.meshgrid(np.arange(xmin, xmax + 1), np.arange(ymin, ymax + 1))
        a = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / denominator
        b = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / denominator
        c = 1 - a - b
        z = a * triangle[0, 2] + b * triangle[1, 2] + c * triangle[2, 2]
        region = np.s_[ymin : ymax + 1, xmin : xmax + 1]
        visible = (a >= -1e-9) & (b >= -1e-9) & (c >= -1e-9) & (z > depth[region])
        depth[region][visible] = z[visible]
        image[region][visible, :3] = color
        image[region][visible, 3] = 255
    return image, [low[0], high[0], low[1], high[1]]


def render_views(mesh, output: Path) -> list[str]:  # noqa: ANN001
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    views = [("isometric", 28, -55), ("front", 0, -90), ("right", 0, 0), ("top", 90, -90)]
    paths = []
    labels = {
        "front": ("X (mm)", "Z (mm)"),
        "right": ("Y (mm)", "Z (mm)"),
        "top": ("X (mm)", "Y (mm)"),
        "isometric": ("Projected horizontal (mm)", "Projected vertical (mm)"),
    }
    for name, elevation, azimuth in views:
        figure, axis = plt.subplots(figsize=(7, 6), dpi=120)
        try:
            pixels, extent = _rasterize(mesh, elevation, azimuth)
            axis.imshow(pixels, origin="lower", extent=extent, interpolation="nearest", zorder=2)
            axis.set_xlabel(labels[name][0])
            axis.set_ylabel(labels[name][1])
            axis.set_axisbelow(True)
            axis.grid(color="#dce2e8", linewidth=0.6)
            axis.set_title(
                f"{name.title()} | " + " × ".join(f"{n:.1f}" for n in mesh.extents) + " mm"
            )
            figure.tight_layout()
            path = f"{name}.png"
            # Keep the same canvas across views; automatic cropping changes image size.
            figure.savefig(output / path, facecolor="white")
            paths.append(path)
        finally:
            plt.close(figure)
    return paths


def write_preview(report: dict, output: Path) -> None:
    cards = []
    for name in report["views"]:
        data = base64.b64encode((output / name).read_bytes()).decode("ascii")
        cards.append(f'<img alt="{html.escape(name)}" src="data:image/png;base64,{data}">')
    checks = "".join(
        f"<li>{'PASS' if c['passed'] else 'FAIL'}: "
        f"{html.escape(c['name'])} — {html.escape(c['message'])}</li>"
        for c in report["checks"]
    )
    content = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Design inspection</title><style>
body{{font:16px system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem;background:#f5f7fa}}
.views{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem}}
img{{width:100%;border-radius:12px}}pre{{overflow:auto;background:white;padding:1rem}}
</style><h1>Design inspection</h1><p>{html.escape(report["brief"])}</p>
<p>Build: {html.escape(report["build_id"])}. Mechanical checks: {report["passed"]}.
Visual review and slicer inspection are still required.</p>
<div class="views">{"".join(cards)}</div><ul>{checks}</ul>
<h2>Measurements</h2><pre>{html.escape(json.dumps(report["metrics"], indent=2))}</pre>
<p><a href="model.stl">STL</a> · <a href="model.step">STEP</a> ·
<a href="report.json">Report</a></p></html>"""
    (output / "preview.html").write_text(content, encoding="utf-8")
