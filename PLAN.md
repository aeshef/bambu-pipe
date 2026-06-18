# Roadmap

`bambu-pipe` is a local-first Python toolkit, not a hosted printing service.
The project should stay useful as a `pip` package, CLI, and optional local
adapters that run near the printer on the user's machine, Raspberry Pi, or home
server.

## Product Positioning

Primary promise:

> Turn a mesh or text prompt into a validated, sliced, LAN-started Bambu Lab print job.

Primary distribution:

- `bambu-pipe`: Python library and CLI.
- `bambu-pipe serve`: optional local API adapter for integrations.
- `voice2bambu`: optional Telegram adapter that talks to the local API.

Explicit non-goals:

- No hosted SaaS backend.
- No subscriptions, accounts, or multi-tenant printer management.
- No cloud-only printer control.
- No monolithic desktop app.
- No extra languages unless they solve a concrete packaging or integration problem.

## Architecture Rules

- Core package owns configuration, jobs, stages, validation, slicing, and printer transport.
- Adapters are thin: CLI, local REST API, Telegram, future Home Assistant/MCP bridges.
- Providers are replaceable and configured through settings, not hardcoded maps.
- Printer-specific behavior lives behind protocols and profile registries.
- No local machine paths, IPs, access codes, API keys, generated files, caches, or databases in git.
- Public APIs should be small, typed, documented, and stable before v1.0.
- Tests may use fakes; runtime code must use real providers or fail with a clear configuration error.

## v0.1 Baseline

- Bambu Lab A1 LAN / Developer Mode path.
- OrcaSlicer profile registry for A1 material/process selection.
- `mesh_only`: validate, slice, approve, upload, start print.
- `text_full`: Tripo-compatible generation, GLB/STL conversion, validate, slice, approve, print.
- REST API, CLI, Docker local-adapter image, and Telegram adapter.
- SQLite job persistence for local API mode.
- CI, Dependabot, templates, docs, MIT license.

## v0.1.1 - Local Toolkit Polish

- Reposition docs around "local-first Python toolkit" instead of "server product".
- Add public `BambuPipeline` Python API:
  - `BambuPipeline.from_env()`
  - `print_model(...)`
  - `print_prompt(...)`
  - `create_job(...)`
  - `run_job(...)`
- Make REST API clearly optional/local-only.
- Split dependencies into extras:
  - base CLI/core
  - `[api]`
  - `[tripo]`
  - `[dev]`
  - `[all]`
- Add integration examples for library usage.

## v0.2 - Packaging And Reliability

- Publish package metadata for PyPI.
- Add release workflow with trusted publishing once the package name and API stabilize.
- Add local smoke tests for:
  - mesh fixture -> validation -> slicer
  - prompt provider contract -> generated mesh -> slicer
  - printer payload generation
- Add docs for Raspberry Pi / always-on local machine deployment.
- Make `bambu-pipe serve` the official local adapter entrypoint.

## v0.3 - Device And Material Expansion

- Add printer profile packs through registries, not code branches.
- Add A1 Mini / P1 / X1 profile support only after the profile and transport contracts are clean.
- Add material packs through `profiles.json`.
- Add diagnostics that explain material/profile/AMS mismatches before print start.

## v0.4 - Integrations

- Home Assistant example.
- Telegram approval keyboards.
- MCP adapter with a small number of focused local tools.
- Optional UI/preview adapter if it remains local-first and thin.

## Release Gates

- `bambu-pipe doctor` passes on the release machine.
- `ruff check`, `ruff format --check`, and `pytest` pass.
- Staged secret scan finds no local IPs, access codes, API keys, or `/Users/...` paths.
- `mesh_only` fixture STL validates and slices.
- `text_full` with a configured real provider validates and slices.
- Manual A1 smoke starts one known-good print in LAN / Developer Mode.
