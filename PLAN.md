# Roadmap

## Shipped in 0.3

The primary product is an agent-assisted local CAD workflow. A terminal/vision
agent translates the brief into parameterized CadQuery, inspects rendered views
and revises. Local tools export STEP/STL, measure geometry, check requirements
and bind review evidence to the exact revision. The reviewed STL enters the
existing validate/slice/approval/print pipeline.

- Optional CAD engine and rendering extra; no inference API dependency.
- Bundled portable `bambu-design` skill with explicit installation.
- Independent dimension, solid-count, volume and feature-probe contracts.
- Four views, offline preview, build history and stale-review detection.
- Separate visual review, slice inspection and physical-print authorization.
- Real CAD integration tests alongside the existing mesh/API/transport tests.

## Product boundaries

- Keep design and printer operations local; retain optional thin adapters.
- Let the user's coding agent own LLM inference and model choice.
- Prefer dimensioned functional parts for the CAD path; optional Tripo remains
  available for organic assets and carries its own provider cost.
- Do not claim automatic proof of wall thickness, strength, fit or print success.
- Do not execute uploaded CAD Python through the REST API.
- Keep CAD dependencies optional, and preserve existing mesh printing APIs.

## Next, after real usage

- Expand executable feature checks beyond sampled point containment.
- Add a small benchmark of user briefs with measured dimensions, sliced walls
  and actual test-print outcomes. Measure agent success rather than inventing
  a confidence percentage.
- Improve design-specific slicer review and clearance calibration examples.
- Add printer/profile packs only after testing their device and material paths.
- Consider MCP tools if skill users need a stable tool interface beyond the CLI.

## Release checks

Ruff, base tests, real CAD tests and package/wheel checks must pass. Verify the
skill ships in wheels. Inspect real rendered views. Slicing and physical-printer
smokes remain separate checks requiring an installed slicer and actual hardware;
unit tests or CAD exports cannot substitute for them.
