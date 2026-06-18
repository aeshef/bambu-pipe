# OrcaSlicer profiles for Bambu Lab A1

bambu-pipe includes a small A1 profile registry for the default v0.1 path. If
your OrcaSlicer/Bambu Studio version differs, export fresh profiles and point
`BAMBU_PIPE_PROFILES_DIR` at them.

## Export profiles once

1. Open OrcaSlicer.
2. Select **Bambu Lab A1 0.4 nozzle**.
3. Export or save these JSON files into `profiles/bambu_a1/`:

| File | Description |
|------|-------------|
| `profiles.json` | Registry mapping machine/process/material names to profile files |
| `machine.json` | Printer/machine profile |
| `filament_pla.json` | PLA filament profile |
| `filament_petg.json` | PETG filament profile |
| `process_standard.json` | 0.20mm standard process |
| `process_draft.json` | Faster draft process |
| `process_fine.json` | Higher detail process |

4. Point bambu-pipe at the directory:

```bash
export BAMBU_PIPE_PROFILES_DIR=/path/to/profiles/bambu_a1
```

5. Verify:

```bash
bambu-pipe doctor
```

## Add another material

Export the filament profile from OrcaSlicer into the same directory, then add it
to `profiles.json`:

```json
{
  "materials": {
    "TPU": "filament_tpu.json"
  }
}
```

Run with:

```bash
bambu-pipe print --model part.stl --material TPU
```

## Test fixtures

Minimal profile JSON files used only by unit tests live in `tests/fixtures/profiles/`.
