"""Rebuild saved launch cases; no model inference or automatic visual acceptance."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from bambu_pipe.design.workspace import build_design

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "cad" / "desk-hook"
CASES = {"desk24": "spec.json", "desk32": "spec-32mm.json", "missing-hole": "spec.json"}


def seed_missing_hole(source: str) -> str:
    """Deliberate negative control, not an observed inference failure."""
    line = "    body = body.cut(screw)"
    if source.count(line) != 1:
        raise ValueError("Expected exactly one pilot-hole cut in the canonical example")
    return source.replace(line, "    body = body  # Intentionally seeded missing pilot hole")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "showcase")
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.exists() and any(destination.iterdir()):
        parser.error("Output must be empty; use a new directory to preserve previous evidence")
    destination.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, spec_name in CASES.items():
        workspace = destination / name
        workspace.mkdir()
        shutil.copy2(EXAMPLE / spec_name, workspace / "spec.json")
        source = (EXAMPLE / "model.py").read_text(encoding="utf-8")
        if name == "missing-hole":
            source = seed_missing_hole(source)
        (workspace / "model.py").write_text(source, encoding="utf-8")
        report = build_design(workspace)
        summary[name] = {
            "build_id": report["build_id"],
            "dimensions_mm": report["metrics"]["dimensions_mm"],
            "passed": report["passed"],
            "passed_checks": sum(check["passed"] for check in report["checks"]),
            "total_checks": len(report["checks"]),
            "failed_checks": [check["name"] for check in report["checks"] if not check["passed"]],
            "seeded_negative_control": name == "missing-hole",
        }
        expected = ["probe:screw through hole"] if name == "missing-hole" else []
        if summary[name]["failed_checks"] != expected:
            raise RuntimeError(f"Unexpected geometry result for {name}: {summary[name]}")
        print(name, json.dumps(summary[name]))
    (destination / "cases.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("Open each passing build's four PNGs, inspect them, then record your own review.")


if __name__ == "__main__":
    main()
