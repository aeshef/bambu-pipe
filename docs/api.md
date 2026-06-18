# Local REST API

Base path: `/api/v1`.

The REST API is an optional local adapter for integrations running near the
printer. It is not designed as a hosted multi-tenant service.

Run it with:

```bash
bambu-pipe serve --host <local-adapter-host> --port 8080
```

- `GET /health`
- `GET /doctor`
- `GET /printer/status`
- `POST /jobs`
- `POST /jobs/upload`
- `POST /jobs/print`
- `GET /jobs/{id}`
- `GET /jobs/{id}/preview`
- `POST /jobs/{id}/run`
- `POST /jobs/{id}/approve`
- `POST /jobs/{id}/cancel`

For safety, REST `POST /jobs` does not accept arbitrary server-local
`model_path` values. Use `POST /jobs/upload` for mesh input, or
`POST /jobs/print` for upload-and-run.

## Upload And Run

```bash
export BAMBU_PIPE_API_BASE_URL="http://<local-adapter-host>:8080/api/v1"

curl -X POST "$BAMBU_PIPE_API_BASE_URL/jobs/print?auto_approve=true&material=PETG" \
  -F "file=@./model.stl"
```

## Text-To-3D

Text generation uses the Tripo-compatible provider. Configure:

```bash
BAMBU_PIPE_TRIPO_API_KEY=...
```

Then create and run a job:

```bash
curl -X POST "$BAMBU_PIPE_API_BASE_URL/jobs" \
  -H 'Content-Type: application/json' \
  -d '{"mode":"text_full","prompt":"small low-poly cat figurine","auto_approve":false}'
```
