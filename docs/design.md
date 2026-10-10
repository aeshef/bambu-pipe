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
