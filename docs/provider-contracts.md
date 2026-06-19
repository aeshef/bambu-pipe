# Provider And Device Contracts

`bambu-pipe` should grow by adding explicit capabilities, not device-specific
branches in adapters.

## Current Stable Path

- Printer: Bambu Lab A1.
- Transport: LAN / Developer Mode over FTPS and MQTT.
- Slicer: local OrcaSlicer/Bambu Studio-compatible CLI.
- Profiles: bundled A1 profile pack or `BAMBU_PIPE_PROFILES_DIR`.
- Mesh provider: Tripo-compatible `text_to_model`.

## Extension Rules

- Adapters must call `BambuPipeline` or `PipelineOrchestrator`, not printer or
  slicer internals.
- New mesh providers implement `MeshProvider`.
- New slicers should expose the same `SliceResult` contract.
- New printers should define a capability object before adding payload or status
  code branches.
- Runtime code should use real providers or fail with `ConfigError`; tests may use
  fakes.

## Future Printer Capability Shape

A future printer profile should describe:

- model name and build volume;
- upload transport and required ports;
- start-print payload builder;
- status parser and error-code mapping;
- slicer machine/profile pack;
- bed type and calibration defaults;
- AMS/material policy;
- startup monitoring policy.

This keeps A1, A1 Mini, P1, and X1 support as data-backed capabilities instead
of conditionals spread across `printer/`, `providers/slicer/`, and adapters.
