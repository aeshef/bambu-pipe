# bambu-pipe

Headless pipeline from a 3D mesh to a printed object on a Bambu Lab A1.

**Scope in v0.1:** LAN-only Bambu Lab A1 flow — validate → slice → print, plus a
pluggable text-to-3D generation stage for providers such as Tripo.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e "packages/bambu_pipe[dev]"
cp .env.example .env
# edit .env with printer IP, serial, access code
bambu-pipe doctor
```

Export OrcaSlicer profiles for your A1 into `profiles/bambu_a1/` and register
materials in `profiles/bambu_a1/profiles.json` — see [profiles/README.md](profiles/README.md).

## CLI

```bash
# Validate environment
bambu-pipe doctor

# Mesh-only pipeline (approval gates skipped with --yes)
bambu-pipe print --model ./model.stl --yes

# Choose any material key configured in profiles.json
bambu-pipe print --model ./model.stl --material PETG --yes

# Text-to-print pipeline through the configured Tripo-compatible provider
bambu-pipe print "small low-poly cat figurine"

# Printer status
bambu-pipe status
```

## API

```bash
pip install -e "packages/bambu_pipe[api]"
uvicorn apps.api.main:create_app --factory --reload --port 8080
```

```bash
curl http://localhost:8080/api/v1/health
curl -X POST "http://localhost:8080/api/v1/jobs/upload?auto_approve=true" \
  -F "file=@./model.stl"
curl -X POST http://localhost:8080/api/v1/jobs/<id>/run
curl -X POST http://localhost:8080/api/v1/jobs/<id>/approve -d '{"approved":true}'
```

For one-shot REST printing, use `POST /api/v1/jobs/print` with the same multipart
parameters as `/jobs/upload`. REST intentionally rejects arbitrary server-local
paths; adapters that need local files should call the internal orchestrator API.

Text-to-3D uses the Tripo-compatible provider by default. Set
`BAMBU_PIPE_TRIPO_API_KEY=...`, then create a `text_full` job with a prompt.

## Docker

```bash
cp .env.example .env
# edit .env and profiles/bambu_a1/profiles.json
docker compose -f docker/compose.yml up --build
```

The API container expects printer LAN access and mounted Orca profiles. Local
OrcaSlicer execution inside Docker requires mounting or installing the slicer
binary in the container image.

## Architecture

- `bambu_pipe.stages.*` — atomic pipeline stages with protocols
- `bambu_pipe.printer.base.PrinterClient` — printer-provider contract
- `bambu_pipe.models.validation.ValidationReport` — Print Confidence Score from validation checks
- `bambu_pipe.orchestrator.PipelineOrchestrator` — resumable state machine with approval gates
- `apps/api` — thin FastAPI adapter

## Requirements

- Python 3.11+
- OrcaSlicer installed locally
- Bambu Lab printer on LAN with **Developer Mode** enabled
- Exported Orca profiles for your printer

## Docs

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Printer setup](docs/printer-setup.md)
- [API](docs/api.md)

## License

MIT
