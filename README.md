# bambu-pipe

[![CI](https://github.com/aeshef/bambu-pipe/actions/workflows/ci.yml/badge.svg)](https://github.com/aeshef/bambu-pipe/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/aeshef/bambu-pipe?include_prereleases&label=release)](https://github.com/aeshef/bambu-pipe/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Printer](https://img.shields.io/badge/printer-Bambu%20Lab%20A1-orange.svg)](docs/printer-setup.md)
[![Mode](https://img.shields.io/badge/mode-LAN%20Developer%20Mode-black.svg)](docs/printer-setup.md)
[![Local First](https://img.shields.io/badge/local--first-no%20cloud-black)](docs/architecture.md)

![bambu-pipe logo](docs/assets/logo.svg)

Turn a mesh or text prompt into a validated, sliced, LAN-started print on a
Bambu Lab A1.

`bambu-pipe` is a local-first Python toolkit for builders who want automation
without a desktop slicer UI, cloud lock-in, hosted accounts, or fragile printer
scripts.

[Getting Started](#quick-start) · [Python API](docs/python-api.md) · [Docs](docs/architecture.md) · [Printer Setup](docs/printer-setup.md) · [Configuration](docs/configuration.md) · [Tripo Smoke](docs/tripo-smoke.md) · [Release Process](docs/release.md) · [Roadmap](PLAN.md) · [Security](SECURITY.md) · [Support](SUPPORT.md) · [Issues](https://github.com/aeshef/bambu-pipe/issues)

## Why It Exists

Most 3D printing workflows still stop at the boring parts: open a slicer, pick
profiles, export a project file, upload it, start the job, check whether the
printer accepted it, then repeat when something silently fails.

`bambu-pipe` makes that flow programmable:

```text
text prompt or mesh -> validation -> OrcaSlicer -> preview metadata -> approval -> Bambu A1
```

## Highlights

- Headless A1 LAN printing over FTPS and MQTT.
- OrcaSlicer integration with profile registry driven by JSON, not Python mappings.
- `mesh_only` jobs for existing STL/OBJ/3MF/GLB assets.
- `text_full` jobs through a Tripo-compatible text-to-3D provider.
- Print Confidence Score from validation checks.
- Approval gates before slicing and printing.
- Python API, CLI, optional local REST adapter, Docker local-adapter image, and Telegram voice adapter.
- SQLite job persistence for API mode.
- Secret-safe REST uploads: no arbitrary server-local `model_path` from HTTP clients.
- Open-source hygiene: CI, Dependabot, issue templates, docs, MIT license.

## Quick Start

```bash
git clone https://github.com/aeshef/bambu-pipe.git
cd bambu-pipe

python -m venv .venv
source .venv/bin/activate
pip install -e "packages/bambu_pipe[all]"

cp .env.example .env
# Fill printer IP, serial, access code, and provider keys.

bambu-pipe doctor
```

For printer setup, see [`docs/printer-setup.md`](docs/printer-setup.md). For
OrcaSlicer profiles and material registry details, see
[`profiles/README.md`](profiles/README.md).

## CLI

```bash
# Validate local setup.
bambu-pipe doctor

# Check a model without slicing or touching the printer.
bambu-pipe validate --model ./model.stl

# Slice locally and inspect preview metadata without uploading.
bambu-pipe preview --model ./model.stl --material PETG

# Slice and start a local model.
bambu-pipe print --model ./model.stl --material PETG --yes

# Generate a model from text, then validate, slice, approve, and print.
bambu-pipe print "small low-poly cat figurine"

# Read printer state over LAN MQTT.
bambu-pipe status
```

## Python API

```python
import asyncio

from bambu_pipe import BambuPipeline


async def main() -> None:
    pipeline = BambuPipeline.from_env()
    await pipeline.print_model("model.stl", material="PETG", auto_approve=True)
    await pipeline.print_prompt("small low-poly cat figurine")


asyncio.run(main())
```

More runnable snippets live in [`examples/`](examples/).

## Local REST Adapter

The REST API is an optional local adapter for integrations. It is not a hosted
service and should not be exposed directly to the public internet.

```bash
pip install -e "packages/bambu_pipe[api]"
bambu-pipe serve --host <local-adapter-host> --port 8080
```

```bash
export BAMBU_PIPE_API_BASE_URL="http://<local-adapter-host>:8080/api/v1"

curl "$BAMBU_PIPE_API_BASE_URL/health"

curl -X POST "$BAMBU_PIPE_API_BASE_URL/jobs/upload?auto_approve=true" \
  -F "file=@./model.stl"

curl -X POST "$BAMBU_PIPE_API_BASE_URL/jobs/<id>/run"
curl "$BAMBU_PIPE_API_BASE_URL/jobs/<id>/preview"
curl -X POST "$BAMBU_PIPE_API_BASE_URL/jobs/<id>/approve" \
  -H "Content-Type: application/json" \
  -d '{"approved":true}'
```

One-shot upload-and-run is available through `POST /api/v1/jobs/print` with the
same multipart parameters as `/jobs/upload`.

## Text-To-Print

`text_full` uses the configured Tripo-compatible provider. Add the key to your
local `.env`:

```bash
BAMBU_PIPE_MESH_PROVIDER=tripo
BAMBU_PIPE_TRIPO_API_KEY=...
```

Then create a job through CLI or REST:

```bash
bambu-pipe print "desk toy robot, printable as a single object"
```

## Docker

```bash
cp .env.example .env
docker compose -f docker/compose.yml up --build
```

The API container needs LAN access to the printer and access to Orca profiles.
If slicing inside the container, mount or install an OrcaSlicer binary.

## Architecture

`bambu-pipe` follows a ports-and-adapters design:

- `bambu_pipe.orchestrator.PipelineOrchestrator` owns the state machine.
- `bambu_pipe.stages.*` contains atomic generation, validation, slicing, and print stages.
- `bambu_pipe.providers.*` contains replaceable mesh and slicer providers.
- `bambu_pipe.printer.*` isolates FTPS, MQTT, payload construction, and status parsing.
- Public Python code uses `bambu_pipe.BambuPipeline`.
- `apps/api` and `packages/voice2bambu` stay thin and call the core pipeline.

See [`docs/architecture.md`](docs/architecture.md) for the compact system map.

## Release Status

v0.1 targets one reliable hardware path:

- Bambu Lab A1.
- LAN / Developer Mode.
- OrcaSlicer profiles.
- Mesh upload or Tripo-compatible text generation.
- Approval-gated start over local printer transport.

Not in scope: Bambu cloud mode, warranty support, filament quality problems, or
non-A1 profile packs.

## Documentation

- [Architecture](docs/architecture.md)
- [Python API](docs/python-api.md)
- [Configuration](docs/configuration.md)
- [Printer setup](docs/printer-setup.md)
- [Real Tripo smoke test](docs/tripo-smoke.md)
- [REST API](docs/api.md)
- [Profiles and materials](profiles/README.md)
- [Roadmap](PLAN.md)
- [Release process](docs/release.md)
- [Security policy](SECURITY.md)
- [Support](SUPPORT.md)

## Contributing

Issues and PRs are welcome. Please include:

- `bambu-pipe doctor` output with secrets removed.
- Printer model and firmware version.
- Material, profile, and AMS/external filament mode.
- The exact command or API request that failed.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and the PR template.

## Contact

- GitHub: [aeshef/bambu-pipe](https://github.com/aeshef/bambu-pipe)
- Issues: [github.com/aeshef/bambu-pipe/issues](https://github.com/aeshef/bambu-pipe/issues)

## License

MIT. Bambu Lab is a trademark of its owner; this project is independent and not
affiliated with Bambu Lab.
