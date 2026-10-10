"""Real CAD/export/render tests; optional in base installs, mandatory in CAD CI."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pytest
from bambu_pipe.cli.main import app
from bambu_pipe.design.workspace import (
    DesignError,
    build_design,
    init_design,
    review_design,
    verify_design,
)
from typer.testing import CliRunner

cq = pytest.importorskip("cadquery")
pytest.importorskip("matplotlib")

VIEWS = ["isometric.png", "front.png", "right.png", "top.png"]


@pytest.fixture(scope="module")
def built_plate(tmp_path_factory):  # noqa: ANN001
    workspace = init_design(tmp_path_factory.mktemp("cad") / "plate")
    report = build_design(workspace)
    return workspace, report


@pytest.fixture
def workspace(built_plate, tmp_path):  # noqa: ANN001
    source, _ = built_plate
    return Path(shutil.copytree(source, tmp_path / "plate"))


def accept(workspace: Path) -> None:
    review_design(
        workspace,
        decision="accept",
        reviewer="test reviewer",
        notes="Checked two through holes and central web against the brief.",
        viewed=VIEWS,
    )


def test_real_plate_exports_step_stl_and_inspection_views(built_plate) -> None:  # noqa: ANN001
    _, report = built_plate
    assert report["passed"]
    assert report["metrics"]["dimensions_mm"] == pytest.approx([80, 40, 4])
    expected_volume = 80 * 40 * 4 - 2 * math.pi * 2.5**2 * 4
    assert report["metrics"]["volume_mm3"] == pytest.approx(expected_volume)
    imported = cq.importers.importStep(str(Path(report["output_dir"]) / "model.step"))
    assert imported.val().Volume() == pytest.approx(expected_volume)
    for name in VIEWS:
        from PIL import Image

        with Image.open(Path(report["output_dir"]) / name) as image:
            assert image.width >= 600 and image.height >= 500
            assert image.convert("L").getextrema()[0] < 100

    import trimesh
    from bambu_pipe.design.render import _rasterize

    mesh = trimesh.load(Path(report["output_dir"]) / "model.stl", force="mesh")
    pixels, (xmin, xmax, ymin, ymax) = _rasterize(mesh, 90, -90)

    def opacity_at(x: float, y: float) -> int:
        column = int((x - xmin) / (xmax - xmin) * pixels.shape[1])
        row = int((y - ymin) / (ymax - ymin) * pixels.shape[0])
        return int(pixels[row, column, 3])

    assert opacity_at(0, 0) == 255  # Central web remains visible.
    assert opacity_at(-30, 0) == opacity_at(30, 0) == 0  # Through holes stay open.


def test_depth_render_hides_far_faces_independently_of_triangle_order() -> None:
    import numpy as np
    import trimesh
    from bambu_pipe.design.render import _rasterize

    vertices = [[-1, -1, 0], [1, -1, 0], [0, 1, 0], [-1, -1, 1], [1, -1, 1], [0, 1, 1]]
    # Near face has opposite winding, so its color differs from the hidden far face.
    mesh = trimesh.Trimesh(vertices=vertices, faces=[[0, 1, 2], [3, 5, 4]], process=False)
    pixels, _ = _rasterize(mesh, 90, -90, width=140, height=100)
    reversed_mesh = trimesh.Trimesh(vertices=vertices, faces=mesh.faces[::-1], process=False)
    reversed_pixels, _ = _rasterize(reversed_mesh, 90, -90, width=140, height=100)
    assert np.array_equal(pixels, reversed_pixels)
    assert pixels[50, 70].tolist() == [25, 66, 86, 255]


def test_review_requires_images_and_is_not_implicit(workspace) -> None:  # noqa: ANN001
    with pytest.raises(DesignError, match="missing"):
        verify_design(workspace)
    with pytest.raises(DesignError, match="four"):
        review_design(workspace, decision="accept", reviewer="test", notes="ok", viewed=VIEWS[:1])
    accept(workspace)
    assert verify_design(workspace)["verified"]


@pytest.mark.parametrize(
    "target",
    [
        "model.py",
        "spec.json",
        "model.stl",
        "model.step",
        "top.png",
        "metrics.json",
        "preview.html",
        "report.json",
    ],
)
def test_any_input_or_artifact_change_invalidates_review(workspace, target) -> None:  # noqa: ANN001
    accept(workspace)
    latest = json.loads((workspace / "latest.json").read_text())
    output = workspace / "builds" / latest["build_id"]
    path = workspace / target if target in {"model.py", "spec.json"} else output / target
    path.write_bytes(path.read_bytes() + b"\nchanged")
    with pytest.raises(DesignError, match="changed"):
        verify_design(workspace)


def test_rebuild_requires_a_new_review(workspace) -> None:  # noqa: ANN001
    accept(workspace)
    previous = verify_design(workspace)["build_id"]
    rebuilt = build_design(workspace)
    assert rebuilt["build_id"] != previous
    with pytest.raises(DesignError, match="missing"):
        verify_design(workspace)
    assert (workspace / "builds" / previous / "review.json").is_file()


def test_missing_holes_are_detected_against_independent_spec(workspace) -> None:  # noqa: ANN001
    (workspace / "model.py").write_text(
        "import cadquery as cq\ndef build(p):\n"
        '    return cq.Workplane("XY").box(80, 40, 4, centered=(True,True,False))\n'
    )
    report = build_design(workspace)
    assert not report["passed"]
    assert any(c["name"] == "probe:left through hole" and not c["passed"] for c in report["checks"])
    with pytest.raises(DesignError, match="Mechanical"):
        accept(workspace)
    review_design(
        workspace,
        decision="revise",
        reviewer="test reviewer",
        notes="Required holes are missing.",
        viewed=VIEWS,
    )
    with pytest.raises(DesignError, match="Mechanical"):
        verify_design(workspace)


def test_wrong_size_is_not_auto_scaled(workspace) -> None:  # noqa: ANN001
    path = workspace / "model.py"
    path.write_text(path.read_text().replace('p["width"]', 'p["width"] * 0.5'))
    report = build_design(workspace)
    assert not report["passed"]
    assert any(c["name"] == "dimensions" and not c["passed"] for c in report["checks"])


def test_disconnected_parts_fail_single_solid_contract(workspace) -> None:  # noqa: ANN001
    (workspace / "model.py").write_text(
        "import cadquery as cq\ndef build(p):\n"
        '    left = cq.Workplane("XY").box(30,40,4, centered=(True,True,False))'
        ".translate((-25,0,0))\n"
        '    right = cq.Workplane("XY").box(30,40,4, centered=(True,True,False))'
        ".translate((25,0,0))\n"
        "    return cq.Compound.makeCompound([left.val(),right.val()])\n"
    )
    report = build_design(workspace)
    assert not report["passed"]
    assert report["metrics"]["dimensions_mm"] == pytest.approx([80, 40, 4])
    assert any(c["name"] == "solid_count" and not c["passed"] for c in report["checks"])


def test_failed_attempt_cannot_reuse_an_accepted_mesh(workspace) -> None:  # noqa: ANN001
    accept(workspace)
    (workspace / "model.py").write_text('def build(p):\n    raise ValueError("bad design")\n')
    with pytest.raises(DesignError, match="build failed"):
        build_design(workspace)
    assert not (workspace / "latest.json").exists()
    result = CliRunner().invoke(app, ["design", "verify", str(workspace)])
    assert result.exit_code == 2


def test_worker_timeout_invalidates_latest_and_preserves_history(workspace) -> None:  # noqa: ANN001
    (workspace / "model.py").write_text("import time\ndef build(p):\n    time.sleep(60)\n")
    with pytest.raises(DesignError, match="timed out"):
        build_design(workspace, timeout=1)
    assert not (workspace / "latest.json").exists()
    assert len(list((workspace / "builds").iterdir())) == 2


def test_slice_handoff_uses_verified_stl_without_printing(workspace, monkeypatch) -> None:  # noqa: ANN001
    from bambu_pipe.models.job import JobStage, PrintJob
    from bambu_pipe.pipeline import BambuPipeline

    captured = []

    class LocalOnlyPipeline:
        async def slice_model(self, path, **kwargs):  # noqa: ANN001
            captured.append((path, kwargs))
            job = PrintJob(model_path=path)
            job.stage = JobStage.AWAITING_SLICE_APPROVAL
            return job

    monkeypatch.setattr(BambuPipeline, "from_env", lambda: LocalOnlyPipeline())
    # The unreviewed model never even reaches the slicer.
    blocked = CliRunner().invoke(app, ["design", "slice", str(workspace)])
    assert blocked.exit_code == 2 and not captured
    accept(workspace)
    result = CliRunner().invoke(app, ["design", "slice", str(workspace), "--material", "PETG"])
    assert result.exit_code == 0
    assert captured == [
        (verify_design(workspace)["model_path"], {"quality": "standard", "material": "PETG"})
    ]
    assert json.loads(result.stdout)["stage"] == "awaiting_slice_approval"
