# REST API

Base path: `/api/v1`.

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
curl -X POST "http://localhost:8080/api/v1/jobs/print?auto_approve=true&material=PETG" \
  -F "file=@./model.stl"
```

## Text-To-3D

Text generation uses the Tripo-compatible provider. Configure:

```bash
BAMBU_PIPE_TRIPO_API_KEY=...
```

Then create and run a job:

```bash
curl -X POST http://localhost:8080/api/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"mode":"text_full","prompt":"small low-poly cat figurine","auto_approve":false}'
```
