# Changelog

## 0.3.0

- Make agent-assisted parametric CAD the primary design workflow with the bundled `bambu-design` skill.
- Add optional `[cad]` / `[cad-dev]` extras, real CadQuery builds, STEP/STL exports, four CPU-rendered views and offline HTML inspection.
- Add strict dimension/spec contracts and material/void probes for feature checks.
- Add build history, source/spec/artifact hashes, explicit visual review and stale-review rejection.
- Add `design slice` to hand the verified STL to the existing local pipeline without contacting the printer.
- Preserve millimeter dimensions and print orientation during slicing; remove implicit 100× scaling of small STL files and automatic orientation changes.
- Resolve BBL slicer profile inheritance to full JSON settings, reject missing/cyclic parents and report native CLI crashes explicitly.
- Block empty, non-finite, open and incorrectly wound meshes before slicing.
- Stop using mesh-edge lengths as wall thickness; measure bed contact area, label scores as heuristics and exclude bed faces from overhang warnings.
- Add real CAD integration tests, a CAD CI job and packaged-skill wheel checks.
- Remove unused LLM settings; agent inference belongs to the user's agent harness.

## 0.2.0

- Add `bambu-pipe print --dry-run` to produce a complete local print plan without contacting the printer.
- Generate `preview.html`, preview image copies, and `artifact-manifest.json` for sliced jobs.
- Add validation warnings for tiny/huge scale, bed contact, overhang risk, and thin-feature risk.
- Add `jobs show`, `jobs artifacts`, `jobs retry`, and JSON output for persisted job history.
- Save Tripo provider create/poll payloads as job artifacts for debugging real text-to-3D runs.
- Add `BambuPipeline.plan_print()` for scripts and adapters that need a no-print planning contract.

## 0.1.2

- Add optional token protection for mutating local REST API routes.
- Refuse unsafe non-loopback REST binds unless an API token or explicit risk flag is configured.
- Bundle default A1 Orca profile pack in the `bambu-pipe` wheel.
- Expand CI to build `voice2bambu`, smoke-test wheel installs, scan for obvious secrets, and build Docker.
- Make CLI job listing use the configured SQLite store.
- Add provider/capability architecture docs for future device expansion.

## 0.1.1

- Add public `BambuPipeline` helpers for model validation, local slicing, prompt printing, and job execution.
- Add CLI dry-run commands: `validate`, `slice`, and `preview`.
- Add release-process documentation, examples, and package build verification in CI.
- Improve Tripo provider error messages for authentication, rate limits, timeouts, failed tasks, and empty outputs.
- Add opt-in overlong slice rejection using `BAMBU_PIPE_MAX_ESTIMATED_PRINT_MINUTES`.
- Accept `OPENROUTER_API_KEY` and `ASR_*` aliases for local voice transcription configuration.

## 0.1.0

- Initial mesh-only pipeline: validate, slice, upload, and print.
- Tripo-compatible text-to-3D pipeline: prompt, mesh generation, validation, slicing, and approval gates.
- A1 profile registry with configurable materials.
- FastAPI and CLI adapters.
- Telegram `voice2bambu` adapter with OpenAI-compatible voice transcription.
- SQLite job persistence for API mode.
