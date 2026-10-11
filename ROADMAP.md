# Roadmap

## Available in 0.3.0

- Local parametric CAD with an existing terminal/vision agent and a bundled skill.
- STEP/STL, four inspection views, explicit geometric checks and revision-bound review.
- Desk-hook and cable-organizer examples with editable source and acceptance specs.
- Optional Bambu A1 mesh/slice/print adapters; design works without a printer.

## Contributions welcome

- Better installation instructions across operating systems.
- Useful dependency/version diagnostics without configuring a printer.
- Clearer material/void probe evidence in HTML reports.
- Real fit/print reports that include material, orientation, hardware and limitations.

See [open beginner tasks](https://github.com/aeshef/bambu-pipe/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
and [help wanted](https://github.com/aeshef/bambu-pipe/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22).

## Proposals to evaluate

1. A small suite of fixed design briefs and negative controls, with agent-run
   provenance and failure reporting. Geometry pass rate alone is insufficient.
2. More measured feature checks: hole diameter, distances and minimum walls.
3. Reliable native slicer smoke coverage across supported platforms.

These are candidates, not promised dates. A built-in autonomous or multi-agent
service is not part of the current release. Prefer evidence from real usage
before adding another orchestration layer.
