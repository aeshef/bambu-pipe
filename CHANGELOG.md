# Changelog

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
