"""Reproducible local builds with revision-bound review evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from bambu_pipe.design.schema import DesignSpec


class DesignError(ValueError):
    """An actionable design/build/review failure."""


STARTER_MODEL = '''"""Mounting plate; millimeters, XY bed, bottom at Z=0."""
import cadquery as cq


def build(p):
    plate = cq.Workplane("XY").box(
        p["width"], p["depth"], p["thickness"], centered=(True, True, False)
    )
    return (plate.faces(">Z").workplane()
            .pushPoints([(-p["hole_spacing"] / 2, 0), (p["hole_spacing"] / 2, 0)])
            .hole(p["hole_diameter"]))
'''


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def init_design(
    workspace: Path, brief: str = "80 × 40 × 4 mm mounting plate, two 5 mm holes"
) -> Path:
    workspace = workspace.expanduser().resolve()
    if workspace.exists() and any(workspace.iterdir()):
        raise DesignError("Workspace must be empty; existing designs are never overwritten")
    workspace.mkdir(parents=True, exist_ok=True)
    spec = DesignSpec(
        brief=brief,
        parameters={
            "width": 80,
            "depth": 40,
            "thickness": 4,
            "hole_spacing": 60,
            "hole_diameter": 5,
        },
        dimensions_mm=(80, 40, 4),
        probes=[
            {"name": "left through hole", "point_mm": [-30, 0, 2], "expect": "void"},
            {"name": "right through hole", "point_mm": [30, 0, 2], "expect": "void"},
            {"name": "hole reaches radius 2.4", "point_mm": [32.4, 0, 2], "expect": "void"},
            {"name": "material at radius 2.6", "point_mm": [32.6, 0, 2], "expect": "solid"},
            {"name": "center web", "point_mm": [0, 0, 2], "expect": "solid"},
        ],
        assumptions=["Starter geometry only: replace parameters and checks to match the brief."],
    )
    _write_json(workspace / "spec.json", spec.model_dump(mode="json"))
    (workspace / "model.py").write_text(STARTER_MODEL, encoding="utf-8")
    return workspace


def _check(name: str, passed: bool, message: str) -> dict:
    return {"name": name, "passed": bool(passed), "message": message}


def _acceptance_checks(spec: DesignSpec, metrics: dict, mesh) -> list[dict]:  # noqa: ANN001
    import numpy as np

    dimensions = metrics["dimensions_mm"]
    checks = [
        _check("cad_valid", metrics["cad_valid"], "OpenCascade solid validity"),
        _check(
            "solid_count",
            metrics["solid_count"] == spec.solid_count,
            f"{metrics['solid_count']} solids; expected {spec.solid_count}",
        ),
        _check(
            "dimensions",
            all(
                abs(a - b) <= spec.dimension_tolerance_mm
                for a, b in zip(dimensions, spec.dimensions_mm, strict=True)
            ),
            f"CAD {dimensions} mm; expected {list(spec.dimensions_mm)} "
            f"± {spec.dimension_tolerance_mm} mm",
        ),
        _check(
            "bed_fit",
            all(a <= b for a, b in zip(dimensions, spec.bed_mm, strict=True)),
            f"Build volume {list(spec.bed_mm)} mm",
        ),
        _check(
            "volume",
            metrics["volume_mm3"] >= spec.min_volume_mm3,
            f"{metrics['volume_mm3']:.3f} mm³; minimum {spec.min_volume_mm3}",
        ),
        _check(
            "on_bed",
            abs(metrics["bounds_mm"][0][2]) <= 0.05,
            "CAD bottom must be at Z=0 (± 0.05 mm); orientation is not auto-corrected",
        ),
        _check("mesh_watertight", mesh.is_watertight, "Exported STL is closed"),
        _check("mesh_volume", mesh.is_volume, "Exported STL has consistent outward winding"),
        _check(
            "mesh_dimensions",
            np.allclose(mesh.extents, dimensions, atol=0.1, rtol=0),
            f"STL {mesh.extents.tolist()} mm matches CAD within 0.1 mm",
        ),
    ]
    checks.extend(
        _check(
            f"probe:{p['name']}",
            p["passed"],
            "Material detected" if p["inside"] else "Void detected",
        )
        for p in metrics["probes"]
    )
    return checks


def build_design(workspace: Path, timeout: int = 300) -> dict:
    if timeout < 1:
        raise DesignError("Build timeout must be positive")
    for dependency in ("cadquery", "matplotlib"):
        if importlib.util.find_spec(dependency) is None:
            raise DesignError('Install the CAD extra: pip install "bambu-pipe[cad]"')
    workspace = workspace.expanduser().resolve()
    spec_path, source_path = workspace / "spec.json", workspace / "model.py"
    spec = DesignSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
    if not source_path.is_file():
        raise DesignError("Workspace must contain model.py with build(parameters)")

    # Invalidate the previous accepted build before starting any new attempt.
    (workspace / "latest.json").unlink(missing_ok=True)
    build_id = uuid.uuid4().hex
    output = workspace / "builds" / build_id
    output.mkdir(parents=True)
    shutil.copy2(source_path, output / "model.py")
    shutil.copy2(spec_path, output / "spec.json")
    spec = DesignSpec.model_validate_json((output / "spec.json").read_text(encoding="utf-8"))
    source_hash, spec_hash = _hash(output / "model.py"), _hash(output / "spec.json")
    worker_env = dict(os.environ)
    # The source checkout may not be installed (tests); preserve its import path in the worker.
    worker_env["PYTHONPATH"] = os.pathsep.join(str(p) for p in sys.path if p)
    worker_env["MPLCONFIGDIR"] = str(output / ".mpl-cache")
    with (output / "worker.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "bambu_pipe.design.worker", str(output)],
            cwd=output,
            env=worker_env,
            stdout=log,
            stderr=log,
            start_new_session=os.name == "posix",
        )
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()
            raise DesignError(f"CAD build timed out; inspect {output / 'worker.log'}") from exc
    if process.returncode:
        raise DesignError(f"CAD build failed; inspect {output / 'worker.log'}")

    import numpy as np
    import trimesh

    from bambu_pipe.design.render import write_preview

    metrics = json.loads((output / "metrics.json").read_text())
    mesh = trimesh.load(output / "model.stl", force="mesh", process=True)
    if (
        not isinstance(mesh, trimesh.Trimesh)
        or not len(mesh.faces)
        or not np.isfinite(mesh.vertices).all()
    ):
        raise DesignError("CAD export is empty or has non-finite coordinates")
    checks = _acceptance_checks(spec, metrics, mesh)
    views = ["isometric.png", "front.png", "right.png", "top.png"]
    report = {
        "schema_version": 1,
        "build_id": build_id,
        "created_at": datetime.now(UTC).isoformat(),
        "brief": spec.brief,
        "source_sha256": source_hash,
        "spec_sha256": spec_hash,
        "metrics": metrics,
        "checks": checks,
        "passed": all(c["passed"] for c in checks),
        "views": views,
        "assumptions": spec.assumptions,
        "limitations": [
            "Point probes sample geometry; they do not prove every feature.",
            "Wall thickness, strength, fit and support strategy require review and slicing.",
            "Mechanical checks are not a probability of print success.",
        ],
    }
    write_preview(report, output)
    names = [
        "model.py",
        "spec.json",
        "model.stl",
        "model.step",
        "metrics.json",
        "preview.html",
        *views,
    ]
    report["artifact_sha256"] = {name: _hash(output / name) for name in names}
    _write_json(output / "report.json", report)
    _write_json(
        workspace / "latest.json",
        {"build_id": build_id, "report_sha256": _hash(output / "report.json")},
    )
    return {**report, "output_dir": str(output)}


def _current_build(workspace: Path, *, require_passed: bool = True) -> tuple[Path, dict, str]:
    workspace = workspace.expanduser().resolve()
    latest = json.loads((workspace / "latest.json").read_text())
    build_id = latest["build_id"]
    if not isinstance(build_id, str) or re.fullmatch(r"[0-9a-f]{32}", build_id) is None:
        raise DesignError("Invalid build ID")
    output = workspace / "builds" / build_id
    report_path = output / "report.json"
    report_hash = _hash(report_path)
    if report_hash != latest["report_sha256"]:
        raise DesignError("Report changed after build; rebuild and review")
    report = json.loads(report_path.read_text())
    if (
        _hash(workspace / "model.py") != report["source_sha256"]
        or _hash(workspace / "spec.json") != report["spec_sha256"]
    ):
        raise DesignError("Source or specification changed; rebuild and review")
    for name, expected in report["artifact_sha256"].items():
        if Path(name).name != name or _hash(output / name) != expected:
            raise DesignError(f"Artifact {name} changed after build; rebuild and review")
    if require_passed and (not report["passed"] or not all(c["passed"] for c in report["checks"])):
        raise DesignError("Mechanical checks failed; repair the model before accepting it")
    return output, report, report_hash


def review_design(
    workspace: Path, *, decision: str, reviewer: str, notes: str, viewed: list[str]
) -> dict:
    if decision not in {"accept", "revise"} or not reviewer.strip() or not notes.strip():
        raise DesignError("Review needs accept/revise, a reviewer and substantive notes")
    output, report, report_hash = _current_build(workspace, require_passed=decision == "accept")
    if not set(viewed).issubset(report["views"]):
        raise DesignError("Review references an unknown inspection view")
    if decision == "accept" and set(viewed) != set(report["views"]):
        raise DesignError("Accept requires inspection of all four PNG views")
    review = {
        "decision": decision,
        "reviewer": reviewer,
        "notes": notes,
        "viewed": viewed,
        "build_id": report["build_id"],
        "report_sha256": report_hash,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _write_json(output / "review.json", review)
    return review


def verify_design(workspace: Path) -> dict:
    output, report, report_hash = _current_build(workspace)
    review_path = output / "review.json"
    if not review_path.is_file():
        raise DesignError("Visual review is missing; inspect the PNGs and record a review")
    review = json.loads(review_path.read_text())
    if (
        review.get("decision") != "accept"
        or review.get("report_sha256") != report_hash
        or review.get("build_id") != report["build_id"]
        or set(review.get("viewed", [])) != set(report["views"])
        or not review.get("notes", "").strip()
        or not review.get("reviewer", "").strip()
    ):
        raise DesignError("Current build has no matching accepted visual review")
    return {
        "verified": True,
        "build_id": report["build_id"],
        "model_path": str(output / "model.stl"),
        "step_path": str(output / "model.step"),
        "preview_path": str(output / "preview.html"),
        "review": review,
    }


def install_skill(target: Path) -> Path:
    source = Path(__file__).resolve().parents[1] / "skills" / "bambu-design"
    destination = target.expanduser().resolve() / "bambu-design"
    if destination.exists():
        raise DesignError(f"Skill already exists at {destination}; inspect it before updating")
    shutil.copytree(source, destination)
    return destination
