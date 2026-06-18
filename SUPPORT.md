# Support

The fastest way to get help is to open a GitHub issue with enough diagnostic
context for another maintainer to reproduce the problem.

## Before Opening An Issue

Run:

```bash
bambu-pipe doctor
```

Remove secrets before sharing output.

## Include This Context

- `bambu-pipe` version or commit SHA.
- Operating system and Python version.
- Printer model and firmware version.
- LAN / Developer Mode status.
- Slicer binary and profile directory.
- Material, AMS/external filament mode, and AMS slot if relevant.
- Exact CLI command or REST request.
- Error message and job ID if available.

## Support Boundaries

Supported in v0.1:

- Bambu Lab A1.
- LAN / Developer Mode.
- OrcaSlicer profile-driven slicing.
- Local Python API, CLI, and optional local REST adapter.

Not supported:

- Cloud-only printer control.
- Hosted multi-tenant deployments.
- Warranty claims or filament quality issues.
- Printer models without a tested profile/transport path.
