# Architecture

`bambu-pipe` is a ports-and-adapters pipeline:

- Public facade: `bambu_pipe.BambuPipeline`.
- Adapters: CLI, optional local REST API, and `voice2bambu`.
- Orchestrator: job state machine, approval gates, and printer queue.
- Stages: generate, validate, slice, and print.
- Providers: slicer, mesh generation, printer transport.

Adapters must not call printer or slicer internals directly. They create jobs and
drive approvals through the orchestrator.
