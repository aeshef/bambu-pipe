# Real Tripo Smoke Test

Use this checklist before claiming that `text_full` works with a real provider.

## What You Need

- `BAMBU_PIPE_TRIPO_API_KEY` in local `.env`.
- Active Tripo account access and enough credits for one small generation.
- Network access to `BAMBU_PIPE_TRIPO_BASE_URL`.
- OrcaSlicer installed and passing `bambu-pipe doctor`.
- A simple prompt, for example:

```text
small calibration cube, printable as one object
```

## Safe First Run

Start with approval gates enabled so the command stops before printer upload:

```bash
bambu-pipe print "small calibration cube, printable as one object"
```

Expected behavior:

1. Tripo creates a task.
2. `bambu-pipe` polls until the model URL is ready.
3. The model downloads as GLB/STL.
4. GLB/GLTF output is converted to STL.
5. Validation runs.
6. OrcaSlicer produces `.gcode.3mf` and preview metadata.
7. If `BAMBU_PIPE_MAX_ESTIMATED_PRINT_MINUTES` is configured, overlong slices are rejected.
8. The job waits for approval before upload/print.

## Provider Error Meanings

- `HTTP 401` / `HTTP 403`: check `BAMBU_PIPE_TRIPO_API_KEY` and account access.
- `HTTP 429`: rate limit or quota/credits problem.
- `5xx`: provider server issue; retry later.
- `task timed out`: task did not finish within the configured timeout.
- `completed without a downloadable model URL`: provider finished but returned no usable model artifact.
- `empty file`: provider URL returned no model bytes.

## After A Successful Provider Smoke

Run a hardware smoke only with a small, known-safe model and the correct
material/profile settings. If the slice estimate is much longer than expected,
do not approve it unless you intentionally want a long print.
