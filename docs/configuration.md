# Configuration

Configuration is loaded from CLI flags, `BAMBU_PIPE_*` environment variables,
`.env` in the current directory, and the platform config file.

Install only the extras you need:

```bash
pip install "bambu-pipe"          # core library and CLI
pip install "bambu-pipe[api]"     # optional local REST adapter
pip install "bambu-pipe[tripo]"   # text-to-3D provider
pip install "bambu-pipe[all]"     # common local toolkit install
```

Important values:

- `BAMBU_PIPE_PRINTER_IP`
- `BAMBU_PIPE_PRINTER_SERIAL`
- `BAMBU_PIPE_PRINTER_ACCESS_CODE`
- `BAMBU_PIPE_PROFILES_DIR`
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
