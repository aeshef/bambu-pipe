"""The launch example must keep its dimensions and detect the seeded missing hole."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from bambu_pipe.design.workspace import DesignError, build_design, review_design

pytest.importorskip("cadquery")
pytest.importorskip("matplotlib")

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "cad" / "desk-hook"


def prepare(tmp_path: Path, spec: str) -> Path:
    workspace = tmp_path / "hook"
    workspace.mkdir()
    shutil.copy2(EXAMPLE / "model.py", workspace / "model.py")
    shutil.copy2(EXAMPLE / spec, workspace / "spec.json")
    return workspace


@pytest.mark.parametrize("spec,height", [("spec.json", 65.5), ("spec-32mm.json", 73.5)])
def test_desk_hook_variants_match_independent_feature_contract(tmp_path, spec, height):  # noqa: ANN001
    report = build_design(prepare(tmp_path, spec))
    assert report["passed"]
    assert report["metrics"]["dimensions_mm"] == pytest.approx([80, height, 35])
    assert len(report["checks"]) == 22
    assert all(probe["passed"] for probe in report["metrics"]["probes"])
    assert not (Path(report["output_dir"]) / "review.json").exists()


def test_seeded_missing_pilot_hole_is_blocked_despite_valid_outer_geometry(tmp_path):  # noqa: ANN001
    from examples.showcase.build_cases import seed_missing_hole

    workspace = prepare(tmp_path, "spec.json")
    path = workspace / "model.py"
    path.write_text(seed_missing_hole(path.read_text()))
    report = build_design(workspace)
    assert not report["passed"]
    assert [check["name"] for check in report["checks"] if not check["passed"]] == [
        "probe:screw through hole"
    ]
    with pytest.raises(DesignError, match="Mechanical checks failed"):
        review_design(
            workspace,
            decision="accept",
            reviewer="negative control test",
            notes="Acceptance must be blocked before any visual review can approve this control.",
            viewed=["isometric.png", "front.png", "right.png", "top.png"],
        )
