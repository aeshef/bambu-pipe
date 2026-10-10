---
name: bambu-design
description: Create and revise dimensioned 3D-printable parts using local CadQuery builds, multi-view visual inspection, geometry checks and Bambu slicing. Use for brackets, mounts, organizers, enclosures and other parametric parts; not for printer administration or photorealistic organic assets.
---

# Bambu design

Deliver editable CAD source, STEP, STL, inspection images and a reviewed build.
Use the agent's existing reasoning and vision capabilities. The toolkit calls no
LLM service: model choice, subscription and any local inference remain with the
agent harness. A terminal-capable agent is required. An image viewer is required
to accept a visual review.

## Get ready

Run `bambu-pipe design doctor`. Prefer an existing project `.venv-cad` or `.venv`;
if the CLI is absent from PATH, use its executable inside that environment.
If CAD dependencies are missing, use Python 3.11
or 3.12 in a virtual environment and install `bambu-pipe[cad]` (or the checkout
with `pip install -e 'packages/bambu_pipe[cad]'`). No printer configuration,
OrcaSlicer, API key, GPU or graphical CAD application is needed for design.

## Design and inspect

1. Establish the brief: intended use, outer dimensions, mating dimensions,
   clearance, material, build orientation and important features. Ask only for
   missing measurements that change fit or function. State reasonable assumptions
   for a prototype; do not invent measured dimensions.
2. Create an empty workspace with `bambu-pipe design init <workspace> --brief
   '<request>'`. This creates a **mounting-plate example**, not a model inferred
   from the request. Replace `model.py` and `spec.json` before claiming success.
3. Write `build(parameters) -> cadquery.Workplane | cadquery.Shape` in `model.py`.
   Use millimeters, XY as the bed, bottom at Z=0. Return all intended solids.
   Keep tunable measurements in `spec.json.parameters`. Scripts run as local
   Python with a timeout, not in a security sandbox; inspect unfamiliar source
   before executing it.
4. Set independent acceptance criteria in `spec.json`: outer dimensions,
   tolerance, solid count, minimum volume and material/void point probes at
   important holes, recesses and load paths. Read [the contract](references/contract.md)
   when authoring a spec. Derive criteria from the brief, not the model's output.
   Do not weaken a failing requirement merely to get green checks.
5. Run `bambu-pipe design build <workspace> --json`. It creates a new directory
   under `builds/` with source/spec snapshots, STEP/STL, exact CAD metrics,
   `report.json`, four PNG views and an offline `preview.html`. Exit 2 means
   failure. For CAD exceptions read that build's `worker.log`, fix the cause and
   rebuild. Do not reuse files from an older successful build after a failure.
6. Actually open **isometric.png, front.png, right.png and top.png** from this
   build using the image viewer. Compare silhouettes, holes, walls, placement,
   orientation and intended function against the brief. Read the checks and
   recorded assumptions. Green geometry checks do not prove design intent,
   wall thickness, strength, fit or printability. If images cannot be inspected,
   leave the build awaiting review and say so.
7. Fix issues and repeat build → inspect. Default to at most three repair
   iterations before presenting the remaining issue or requesting a critical
   missing measurement. Do not silently change the user's design.
8. When mechanical checks pass and all views have been inspected, record the
   review with concrete observations and remaining assumptions:

   ```bash
   bambu-pipe design review <workspace> --decision accept --reviewer '<agent or human>' \
     --view isometric.png --view front.png --view right.png --view top.png \
     --notes 'Observed geometry, agreement with brief, and remaining assumptions'
   bambu-pipe design verify <workspace>
   ```

   `review` records your attestation; it does not supply an automated visual
   judge. Changes to source, spec, exports, images or report invalidate the
   review. A rebuild requires a new review. Say “reviewed CAD prototype”, not
   “guaranteed printable”.

## Slice and deliver

If a slicer and suitable profiles are installed, run
`bambu-pipe design slice <workspace> --material PLA --quality standard`.
It verifies the accepted build, then validates and slices that exact STL using
the existing pipeline. It never uploads or starts a print. Inspect the sliced
preview and extrusion paths, including thin walls, supports, bridges and bed
contact. If slicing is unavailable, deliver the CAD artifacts and state that
slicer verification remains undone.

Return links to `model.py`, `spec.json`, STEP, STL, the images/preview and
`report.json`, plus the dimensions and unresolved assumptions. Distinguish
checks actually executed from observations and tests still needed. Physical
printing remains a separate user request using the existing print command.
