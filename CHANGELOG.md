# Changelog

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
