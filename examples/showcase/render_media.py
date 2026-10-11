"""Render an explicitly edited CAD replay from reviewed, hash-checked build evidence.

Requires the CAD extra, Pillow (a Matplotlib dependency), and ffmpeg on PATH.
This is an example/launch tool, not part of the public package API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import trimesh
from bambu_pipe.design.render import _rasterize
from bambu_pipe.design.workspace import _current_build, verify_design
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BACKGROUND = "#0b1320"
PANEL = "#142335"
INK = "#f2f6fa"
MUTED = "#99aec2"
CYAN = "#69dbeb"
GREEN = "#81e2ae"
RED = "#ff9b8e"


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("/System/Library/Fonts/Supplemental") / ("Arial Bold.ttf" if bold else "Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu")
        / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def label(draw: ImageDraw.ImageDraw, xy: tuple, text: str, size: int, color=INK, bold=False):
    draw.text(xy, text, font=font(size, bold=bold), fill=color, spacing=8)


def use_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, force="mesh", process=True)
    # Display in use orientation only. The verified STL itself stays side-down on Z=0.
    mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))
    mesh.apply_translation([0, -mesh.extents[1] / 2, 0])
    return mesh


def rendered(mesh: trimesh.Trimesh, azimuth: float, width: int, height: int) -> Image.Image:
    pixels, _ = _rasterize(mesh, 22, azimuth, width=width, height=height)
    return Image.fromarray(pixels[::-1].copy())


def evidence(cases: Path) -> tuple[dict, dict]:
    meshes, reports = {}, {}
    for name in ("desk24", "desk32"):
        verified = verify_design(cases / name)
        _, report, _ = _current_build(cases / name)
        meshes[name] = use_mesh(Path(verified["model_path"]))
        reports[name] = report
    output, report, _ = _current_build(cases / "missing-hole", require_passed=False)
    failed = [check["name"] for check in report["checks"] if not check["passed"]]
    if report["passed"] or failed != ["probe:screw through hole"]:
        raise ValueError("Expected the explicitly seeded missing-hole negative control")
    meshes["missing-hole"] = use_mesh(output / "model.stl")
    reports["missing-hole"] = report
    return meshes, reports


def check_count(report: dict) -> str:
    return f"{sum(check['passed'] for check in report['checks'])}/{len(report['checks'])}"


def card(case: str, model: Image.Image, report: dict, stage: int) -> Image.Image:
    image = Image.new("RGB", (720, 720), BACKGROUND)
    draw = ImageDraw.Draw(image)
    label(draw, (34, 24), "bambu-pipe", 24, CYAN, True)
    label(draw, (516, 28), "EDITED REPLAY", 17, MUTED)
    titles = [
        "Your coding agent.\nNow with CAD.",
        "Change the desk.\nKeep the design.",
        "Skip an important hole?\nThe check blocks it.",
        "A CAD workbench\nfor the agent you have.",
    ]
    label(draw, (34, 78), titles[stage], 39, INK, True)
    draw.rounded_rectangle((24, 204, 696, 550), radius=22, fill=PANEL)
    image.paste(model, (40, 208), model)
    draw = ImageDraw.Draw(image)
    parameters = json.loads(Path(report["_spec_path"]).read_text())["parameters"]
    size = parameters["desk_thickness"]
    label(draw, (48, 224), f"{size:g} mm desk", 24, INK, True)
    label(draw, (48, 260), "+0.5 mm clearance", 18, MUTED)
    label(draw, (48, 514), "Use orientation shown · STL exports on its side", 15, MUTED)
    if stage == 2:
        label(draw, (34, 570), "BLOCKED · screw through hole", 26, RED, True)
        label(draw, (34, 612), "Intentional missing-hole control", 21, MUTED)
    elif stage == 3:
        label(draw, (34, 569), "Editable Python + STEP + STL", 27, GREEN, True)
        label(draw, (34, 613), "MIT · github.com/aeshef/bambu-pipe", 23, INK)
    else:
        label(
            draw,
            (34, 570),
            f"{check_count(report)} geometry checks + visual review",
            26,
            GREEN,
            True,
        )
        label(draw, (34, 612), "Local geometry · your existing agent subscription", 21, MUTED)
    label(draw, (34, 674), "CAD prototype · fit, strength and printing untested", 17, MUTED)
    draw.rectangle((0, 709, 720, 720), fill=PANEL)
    draw.rectangle((0, 709, int(720 * (stage + 1) / 4), 720), fill=CYAN)
    return image


def social_card(mesh: trimesh.Trimesh, report: dict) -> Image.Image:
    image = Image.new("RGB", (1280, 640), BACKGROUND)
    draw = ImageDraw.Draw(image)
    label(draw, (54, 38), "bambu-pipe  /  v0.3.0", 27, CYAN, True)
    label(draw, (54, 120), "Your coding agent.\nNow with CAD.", 63, INK, True)
    label(draw, (56, 303), "Editable Python. STEP. STL.", 30, MUTED)
    draw.rounded_rectangle((54, 382, 635, 438), radius=13, fill=PANEL)
    label(draw, (72, 395), f"{check_count(report)} checks + visual review", 28, GREEN, True)
    label(draw, (56, 491), "github.com/aeshef/bambu-pipe", 26, INK)
    label(draw, (56, 537), "Local CAD · existing agent · MIT", 24, MUTED)
    model = rendered(mesh, -65, 610, 470)
    image.paste(model, (656, 72), model)
    label(draw, (720, 536), "Desk-hook prototype · use orientation", 19, MUTED)
    label(
        draw,
        (56, 600),
        "Agent-authored example. Fit, strength and physical printing untested.",
        18,
        MUTED,
    )
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "output" / "showcase")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "launch-assets")
    parser.add_argument(
        "--preview-assets", type=Path, help="Also copy PNG/GIF to this docs directory"
    )
    args = parser.parse_args()
    executable = shutil.which("ffmpeg")
    if executable is None:
        parser.error("Install ffmpeg to encode the replay (no network service is used)")
    meshes, reports = evidence(args.cases.resolve())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, report in reports.items():
        report["_spec_path"] = str(args.cases.resolve() / name / "spec.json")
    social_card(meshes["desk24"], reports["desk24"]).save(
        output / "social-preview.png", optimize=True
    )
    # A cached turntable is reused at 30 fps. These frames replay existing geometry;
    # they contain no claim about generation latency or live agent activity.
    rotations = 48
    frames = {}
    for name, mesh in meshes.items():
        frames[name] = [
            rendered(mesh, -65 + i * 360 / rotations, 640, 336) for i in range(rotations)
        ]
        print(f"Rendered {name}", flush=True)
    scenes = [("desk24", 0, 6), ("desk32", 1, 6), ("missing-hole", 2, 6), ("desk24", 3, 6)]
    command = [
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "720x720",
        "-framerate",
        "30",
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-movflags",
        "+faststart",
        str(output / "bambu-pipe-demo.mp4"),
    ]
    gifs = []
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        assert process.stdin is not None
        for name, stage, seconds in scenes:
            for index in range(seconds * 30):
                rotation = int(index / (seconds * 30) * rotations) % rotations
                frame = card(name, frames[name][rotation], reports[name], stage)
                process.stdin.write(frame.tobytes())
                if index in (0, 90):
                    frame.save(output / f"scene-{stage}-{index}.png")
                # Compact README preview: four scenes in 12 seconds at 4 fps.
                if index % 15 == 0:
                    gifs.append(frame.resize((480, 480), Image.Resampling.LANCZOS))
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("ffmpeg failed to encode the replay")
    gifs[0].save(
        output / "showcase.gif",
        save_all=True,
        append_images=gifs[1:],
        duration=250,
        loop=0,
        optimize=True,
        disposal=2,
    )
    manifest = {
        "format": "24-second edited CAD replay, 720x720, H.264, 30 fps",
        "provenance": (
            "Saved CAD authored and visually reviewed in a Codex launch-preparation session"
        ),
        "negative_control": "Pilot-hole cut intentionally removed; not an observed agent failure",
        "limitations": "No real-time inference recording, physical fit, slicing or print test",
        "display_transform": (
            "STL rotated -90 degrees about X for use orientation; exports unchanged"
        ),
        "cases": {
            name: {
                "build_id": report["build_id"],
                "source_sha256": report["source_sha256"],
                "spec_sha256": report["spec_sha256"],
                "checks": check_count(report),
                "passed": report["passed"],
            }
            for name, report in reports.items()
        },
        "assets": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in ("social-preview.png", "showcase.gif", "bambu-pipe-demo.mp4")
        },
    }
    (output / "media-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    if args.preview_assets:
        args.preview_assets.mkdir(parents=True, exist_ok=True)
        for name in ("social-preview.png", "showcase.gif"):
            shutil.copy2(output / name, args.preview_assets / name)
    print(f"Media ready: {output}")


if __name__ == "__main__":
    main()
