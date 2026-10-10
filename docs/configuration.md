# Configuration

Configuration is loaded from CLI flags, `BAMBU_PIPE_*` environment variables,
`.env` in the current directory, and the platform config file.

Install only the extras you need:

```bash
pip install "bambu-pipe"          # core library and CLI
pip install "bambu-pipe[cad]"     # local CAD exports, rendering and bundled agent skill
pip install "bambu-pipe[api]"     # optional local REST adapter
pip install "bambu-pipe[tripo]"   # text-to-3D provider
pip install "bambu-pipe[all]"     # API + Tripo (CAD remains an explicit extra)
```

For the primary agent-assisted CAD workflow, use `[cad]` with Python 3.11/3.12.
`design init/build/review/verify` need no `.env`, printer credentials or LLM API
key. Requirements live in the workspace's `spec.json`. `design slice` additionally
uses the slicer/profile settings below. See [the design guide](design.md).

Important values:

- `BAMBU_PIPE_PRINTER_IP`
- `BAMBU_PIPE_PRINTER_SERIAL`
- `BAMBU_PIPE_PRINTER_ACCESS_CODE`
- `BAMBU_PIPE_PROFILES_DIR`
- `BAMBU_PIPE_SLICER_RESOURCE_PROFILES_DIR` (optional location of vendor parent profiles)
- `BAMBU_PIPE_MATERIAL`
- `BAMBU_PIPE_USE_AMS`
- `BAMBU_PIPE_AMS_SLOT`
- `BAMBU_PIPE_MAX_UPLOAD_MB`
- `BAMBU_PIPE_MAX_ESTIMATED_PRINT_MINUTES`
- `BAMBU_PIPE_API_TOKEN`
- `BAMBU_PIPE_MESH_PROVIDER`
- `BAMBU_PIPE_TRIPO_API_KEY`
- `BAMBU_PIPE_TRIPO_BASE_URL`

Default A1 Orca profile templates are bundled in the package. Set
`BAMBU_PIPE_PROFILES_DIR` only when you want to use exported/custom profiles.
Materials are configured in `profiles.json`; do not add material mappings in Python code.

The slicer receives complete JSON profiles. The toolkit resolves BBL inheritance
from the installed application's resource profiles and writes the flattened
machine/process/filament files next to each slice in `resolved-profiles/`.
Local profiles override bundled parents. Missing parents and cycles fail before
launching the slicer. For portable installs set the resource directory explicitly
or supply already complete profiles. See the [Bambu CLI contract](https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage).

`BAMBU_PIPE_MESH_PROVIDER` defaults to `tripo`. `text_full` requires
`BAMBU_PIPE_TRIPO_API_KEY`; without it the job fails at configuration time
instead of silently continuing without generation. Provider URLs are configurable so forks
can point at compatible gateways without code changes.

For a real provider test, see `docs/tripo-smoke.md`.

REST upload size is controlled by `BAMBU_PIPE_MAX_UPLOAD_MB`. The API does not
accept arbitrary `model_path` values from HTTP clients; local paths are reserved
for trusted adapters and CLI/internal orchestration.

`BAMBU_PIPE_MAX_ESTIMATED_PRINT_MINUTES` is optional and disabled by default. When
set, it rejects slices that exceed the configured time budget before upload/print.

`BAMBU_PIPE_API_TOKEN` protects mutating local REST routes when set. Send it as
`Authorization: Bearer <token>` or `X-Bambu-Pipe-Token: <token>`.
