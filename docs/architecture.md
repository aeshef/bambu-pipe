# Architecture

`bambu-pipe` is a ports-and-adapters pipeline:

- Public facade: `bambu_pipe.BambuPipeline`.
- Adapters: CLI, optional local REST API, and `voice2bambu`.
- Orchestrator: job state machine, approval gates, and printer queue.
- Stages: generate, validate, slice, and print.
- Providers: slicer, mesh generation, printer transport.

Adapters must not call printer or slicer internals directly. They create jobs and
drive approvals through the orchestrator.

The current printer capability is Bambu Lab A1 over LAN / Developer Mode. Future
device work should add explicit provider/capability contracts instead of
sprinkling model-specific conditionals through adapters. See
[`provider-contracts.md`](provider-contracts.md).

The optional REST API is a local adapter. Mutating routes are protected when
`BAMBU_PIPE_API_TOKEN` is set, and the CLI refuses non-loopback unauthenticated
binds unless the user passes `--i-understand-local-network-risk`.
