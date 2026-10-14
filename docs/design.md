# Agent-assisted local CAD

The bundled `bambu-design` skill makes a terminal/vision agent the designer and
reviewer, while Python tools own geometry execution, exports and measurements.
The agent can use an existing subscription or a local model. The toolkit makes
no LLM calls in this path. Agent quality matters; green checks are necessary
but not sufficient for a useful part.

## Local tools

| Command | Result |
| --- | --- |
| `design doctor` | CAD dependency availability; no printer config |
| `design init PATH --brief TEXT` | Empty workspace with a mounting-plate starter |
| `design build PATH --json --timeout 300` | Real CAD build, STEP/STL, metrics, four PNGs, offline HTML |
| `design review PATH --decision accept --reviewer NAME --notes TEXT --view FILE ...` | Attestation linked to this build; all four views required for acceptance |
| `design verify PATH` | Check current input/artifact hashes and accepted review; return exact STL path |
| `design slice PATH --material PLA --quality standard` | Verified STL → existing validation and slice pipeline; never print |
| `design install-skill --target DIR` | Copy the packaged skill into an explicit agent skills directory |

Read the bundled [spec contract](../packages/bambu_pipe/src/bambu_pipe/skills/bambu-design/references/contract.md)
for fields and feature-probe examples. `model.py` defines `build(parameters)` and
returns a CadQuery Shape or Workplane. CAD source is trusted executable Python,
with the same filesystem access as the invoking user. A worker process and
runtime timeout isolate failures; they do not sandbox untrusted code.
The default timeout is 300 seconds to accommodate a cold CAD-library startup;
use `--timeout` to set another limit. Inspection images use orthographic
projection and a per-pixel depth buffer so hidden faces do not show through.

## Revision evidence

Each build gets a fresh ID and source/spec snapshots. `latest.json` points to its
hashed report. The report hashes the snapshots, exported STEP/STL, metrics,
images and HTML. An accepted `review.json` binds to the report. `verify` checks
all these files and checks the current editable inputs still match. Any edit or
new build needs new inspection. A failing CAD attempt preserves history but
removes the latest pointer. Do not slice files from an older build to conceal a
failed current attempt. Hashes prevent accidental staleness; they are not
signatures against a malicious reviewer rewriting the entire evidence chain.

Reviews are declarations by an agent or person who actually viewed the PNGs.
The CLI cannot prove that the reviewer inspected an image, nor that the part
matches every semantic requirement. A model without image access must leave
visual review incomplete. Notes should say what was observed and what remains
assumed. Never describe an accepted CAD prototype as certified or guaranteed.

## Failure handling

A build failing its mechanical checks still exports a report and renders for
inspection, and exits 2. Fix the specific requirement in the source and rebuild.
A Python/CAD exception or timeout also exits 2; inspect the new build's
`worker.log`. Failed runs never inherit earlier exports. Logs are local and may
contain output from the CAD script; inspect unfamiliar scripts before execution.
Invalid specs fail before geometry execution.

For optional CAD dependencies use Python 3.11/3.12. If wheels are unavailable on
a platform, see [CadQuery installation](https://cadquery.readthedocs.io/en/latest/installation.html).
The package deliberately keeps the existing core install independent of CAD.

## Print boundary

CAD checks do not estimate support generation, filament usage, print duration,
extrusion widths or mechanical strength. Use the verified STL with the real
slicer and appropriate material/nozzle profiles. Inspect extrusion paths and
supports. `design slice` stops before upload/print. Physical printing uses the
existing explicitly invoked `bambu-pipe print --model ...` command; keep the
slice and printer approval separate from the model review.

The slicer may arrange the part on the plate but keeps the supplied orientation
and millimeter scale. Small STL files are no longer silently enlarged 100×.

Slicer crashes fail visibly and never fall back to an older sliced artifact.
Some installed macOS Bambu Studio builds fail in their GUI plate initialization
even for a small STL passed through the CLI. Use a working headless slicer binary
via `BAMBU_PIPE_SLICER_BINARY` when this occurs. CAD export and review remain
independent of the slicer; do not claim slicing passed after such a failure.

### Local slice handoff checks

The current A1 sender uses a textured PEI plate. Slicing explicitly selects
`Textured PEI Plate` and checks the exported `curr_bed_type` against that choice.
A machine preset's `default_bed_type` alone does not select the active plate in
the CLI: a real test otherwise produced Cool Plate G-code at 35 °C. Other plate
types require matching changes to both slicing and the printer command.

A successful subprocess is not sufficient. The adapter checks the ZIP CRCs,
requires exactly `Metadata/plate_1.gcode` (the path used by the sender), rejects
G-code without extrusion moves, and verifies the plate setting. It removes a
previous destination before a new attempt and saves `slicer-command.json`,
`slicer.log`, and flattened profiles next to each result. These are file-format
and handoff checks, not proof of print quality. Bambu's native plate thumbnail
is preferred over object-selection masks. Print weight parsing supports Bambu
Studio's `total filament weight [g]` header.

On macOS, `~/Applications/BambuStudio.app` is discovered before the system Bambu
Studio copy. On 2026-10-14, Bambu Studio **02.08.02.61** completed real slicing
through `verify_design` and the public `BambuPipeline.slice_model` API:

| Reviewed design | Layer | Layers | Estimated time | Estimated PLA |
| --- | --- | --- | --- | --- |
| Moon Gardener | 0.16 mm | 787 | 4h 20m 32s | 81.35 g |
| Orbital Bloom | 0.20 mm | 890 | 6h 19m 33s | 147.46 g |

Both used A1 / 0.4 mm / Generic PLA / textured PEI at 65 °C. The figure used
build-plate tree supports; the vase used no supports. Actual G1/G2/G3 paths were
inspected, including the vase's roughly 34 mm reservoir bridge. Archive CRCs,
embedded G-code MD5, source and archive SHA-256, extrusion bounds, and the local
send payload were checked. The normal bundled profiles also sliced a 10 mm
cube successfully. Local evidence is in
`output/fun-suite-2026-10-14/print-ready/` (generated artifacts are not committed).

Both jobs stopped at `awaiting_slice_approval`. Upload, MQTT device acceptance,
physical printing, support removal, bridge sag and water tightness remain
untested. See the [official CLI documentation](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage)
and [tested Bambu Studio release](https://github.com/bambulab/BambuStudio/releases/tag/v02.08.02.61).

### Rounded-surface STL export

OpenCascade may tessellate sphere poles or rounded corners into triangles of exactly zero area. The CAD worker removes only those empty triangles before saving the final STL and records `stl_zero_area_faces_removed` in its metrics. It never fills holes, moves vertices, or removes small positive-area triangles. The final saved STL still has to pass the usual topology and size checks.
