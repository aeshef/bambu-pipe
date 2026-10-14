"""CAD worker. Process isolation bounds runtime; it is NOT a Python sandbox."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

from bambu_pipe.design.schema import DesignSpec


def remove_zero_area_faces(mesh) -> int:  # noqa: ANN001
    """Discard empty tessellation artifacts; never fill holes or move vertices."""
    keep = mesh.area_faces > 0
    removed = int((~keep).sum())
    if removed:
        mesh.update_faces(keep)
        mesh.remove_unreferenced_vertices()
    return removed


def main() -> None:
    import cadquery as cq
    import numpy as np
    import trimesh

    from bambu_pipe.design.render import render_views

    output = Path(sys.argv[1]).resolve()
    spec = DesignSpec.model_validate_json((output / "spec.json").read_text())
    namespace = runpy.run_path(str(output / "model.py"))
    builder = namespace.get("build")
    if not callable(builder):
        raise ValueError("model.py must define build(parameters) -> Workplane or Shape")
    result = builder(dict(spec.parameters))
    if isinstance(result, cq.Workplane):
        values = result.vals()
        if not values or not all(isinstance(value, cq.Shape) for value in values):
            raise ValueError("build() must return solids, not a sketch or pending wires")
        shape = cq.Compound.makeCompound(values)
    elif isinstance(result, cq.Shape):
        shape = result
    else:
        raise ValueError("build() must return a CadQuery Workplane or Shape")

    solids = shape.Solids()
    if not solids:
        raise ValueError("CAD result has no solids")
    bounds = shape.BoundingBox()
    probes = []
    for probe in spec.probes:
        inside = any(solid.isInside(cq.Vector(*probe.point_mm)) for solid in solids)
        probes.append(
            {"name": probe.name, "inside": inside, "passed": inside == (probe.expect == "solid")}
        )
    metrics = {
        "cad_valid": bool(shape.isValid()),
        "solid_count": len(solids),
        "dimensions_mm": [bounds.xlen, bounds.ylen, bounds.zlen],
        "bounds_mm": [
            [bounds.xmin, bounds.ymin, bounds.zmin],
            [bounds.xmax, bounds.ymax, bounds.zmax],
        ],
        "volume_mm3": sum(solid.Volume() for solid in solids),
        "probes": probes,
        "cadquery_version": cq.__version__,
    }
    cq.exporters.export(shape, str(output / "model.step"))
    cq.exporters.export(shape, str(output / "model.stl"), tolerance=0.05, angularTolerance=0.1)
    mesh = trimesh.load(output / "model.stl", force="mesh", process=True)
    if (
        not isinstance(mesh, trimesh.Trimesh)
        or not len(mesh.faces)
        or not np.isfinite(mesh.vertices).all()
    ):
        raise ValueError("CAD export is empty or has non-finite coordinates")
    # OCC can emit collapsed triangles at sphere poles and rounded corners.
    # They have no surface area but otherwise make a closed STL fail topology checks.
    removed = remove_zero_area_faces(mesh)
    if not len(mesh.faces):
        raise ValueError("CAD export has no positive-area faces")
    if removed:
        mesh.export(output / "model.stl")
    metrics["stl_zero_area_faces_removed"] = removed
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    render_views(mesh, output)


if __name__ == "__main__":
    main()
