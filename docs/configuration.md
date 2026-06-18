# Configuration

Configuration is loaded from CLI flags, `BAMBU_PIPE_*` environment variables,
`.env` in the current directory, and the platform config file.

Important values:

- `BAMBU_PIPE_PRINTER_IP`
- `BAMBU_PIPE_PRINTER_SERIAL`
- `BAMBU_PIPE_PRINTER_ACCESS_CODE`
- `BAMBU_PIPE_PROFILES_DIR`
- `BAMBU_PIPE_MATERIAL`
- `BAMBU_PIPE_USE_AMS`
- `BAMBU_PIPE_AMS_SLOT`
- `BAMBU_PIPE_MAX_UPLOAD_MB`
- `BAMBU_PIPE_MESH_PROVIDER`
- `BAMBU_PIPE_TRIPO_API_KEY`
- `BAMBU_PIPE_TRIPO_BASE_URL`

Materials are configured in `profiles.json`; do not add material mappings in
Python code.

`BAMBU_PIPE_MESH_PROVIDER` defaults to `tripo`. `text_full` requires
`BAMBU_PIPE_TRIPO_API_KEY`; without it the job fails at configuration time
instead of silently continuing without generation. Provider URLs are configurable so forks
can point at compatible gateways without code changes.

REST upload size is controlled by `BAMBU_PIPE_MAX_UPLOAD_MB`. The API does not
accept arbitrary `model_path` values from HTTP clients; local paths are reserved
for trusted adapters and CLI/internal orchestration.
