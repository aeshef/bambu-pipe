# CAD workspace contract

`model.py` defines `build(parameters)`, returning a CadQuery Workplane containing
solids or a Shape. It should be deterministic, without networking, file export
or calls to a printer. The worker exports STEP and STL itself. Use the Python
source and parameters to preserve editability; STEP alone is not parametric.
Keep geometry code self-contained in `model.py`; auxiliary local scripts and
external input files are not included in the revision fingerprint.

`spec.json` is validated strictly: unknown fields, non-finite values, nonpositive
dimensions and unsupported units are rejected. Coordinates and dimensions are
in **millimeters**. The acceptance schema is:

```json
{
  "schema_version": 1,
  "brief": "80 x 40 x 4 mm plate with two 5 mm through holes, 60 mm apart",
  "units": "mm",
  "parameters": {
    "width": 80, "depth": 40, "thickness": 4,
    "hole_spacing": 60, "hole_diameter": 5
  },
  "dimensions_mm": [80, 40, 4],
  "dimension_tolerance_mm": 0.2,
  "bed_mm": [256, 256, 256],
  "solid_count": 1,
  "min_volume_mm3": 1,
  "probes": [
    {"name": "left hole middle", "point_mm": [-30, 0, 2], "expect": "void"},
    {"name": "right hole middle", "point_mm": [30, 0, 2], "expect": "void"},
    {"name": "web", "point_mm": [0, 0, 2], "expect": "solid"}
  ],
  "assumptions": ["Prototype clearance; validate fit on the actual mating part."]
}
```

The spec's bounding dimensions are measured along XYZ after the chosen print
orientation. Set expectations before running the model. Use separate solid/void
probes near both sides of an expected boundary, several depths for through
holes, and several locations for walls. Keep probes away from the exact surface
(OpenCascade has geometric tolerances). Point samples can detect missing or
undersized holes but do not prove a complete diameter, continuous passage or
minimum wall thickness. Verify those features from CAD and sliced paths too.

Each build checks CAD validity, solid count, dimensions, bed fit, volume, bottom
at Z=0, point probes, STL watertightness/winding and STL/CAD size agreement.
It does not auto-scale, auto-place, repair or merge the model. Such changes could
alter intended fit; revise the source explicitly and rebuild instead.

`latest.json` points to a build and its report hash. Accepted review evidence
binds to that report, whose hashes bind source, spec, CAD/mesh exports and views.
Hashes catch stale reviews and accidental changes; this is not a signed security
boundary against someone rewriting all evidence. CLI stdout from `--json` and
`verify` is machine-readable JSON. Build failure is exit 2; a failed new CAD
attempt invalidates the latest pointer while preserving historical builds.
