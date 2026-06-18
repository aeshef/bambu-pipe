# Roadmap

`bambu-pipe` v0.1 focuses on one reliable path: turn a mesh or text prompt into
a validated, sliced, LAN-started print on a Bambu Lab A1.

## v0.1 Release Scope

- CLI and REST adapters for mesh upload, validation, slicing, approval, and print start.
- Tripo-compatible text-to-3D provider for `text_full` jobs.
- OpenAI-compatible transcription in the `voice2bambu` Telegram adapter.
- OrcaSlicer profile registry for A1 material/process selection without Python hardcoding.
- LAN printer transport over FTPS and MQTT with preflight diagnostics.
- SQLite job persistence for API mode.
- Docker API service, CI, issue templates, contributing guide, and MIT license.

## Release Gates

- `bambu-pipe doctor` passes on the release machine.
- `ruff check`, `ruff format --check`, and `pytest` pass.
- `mesh_only`: fixture STL validates, slices, and produces `.gcode.3mf`.
- `text_full`: configured Tripo-compatible provider returns a mesh that validates and slices.
- Manual A1 smoke: upload and start one known-good sliced file in LAN/Developer Mode.
- `.env`, caches, virtualenvs, generated meshes, G-code, databases, and local reference clones are ignored.

## Backlog

- Additional printer profile packs.
- Additional mesh providers.
- Inline Telegram approval keyboards.
- Optional slicer Docker image with OrcaSlicer installed.
- Rich preview UI and demo media.
- Published PyPI/GHCR release automation.
