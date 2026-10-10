# Architecture

`bambu-pipe` is a ports-and-adapters pipeline:

- Design: an existing terminal/vision agent uses the packaged `bambu-design` skill.
- Local CAD tools: `bambu_pipe.design` owns a strict spec, isolated CadQuery worker,
  measured acceptance checks, headless renders and revision-bound review evidence.
- Design handoff: `design slice` verifies an accepted build, then calls the public
  facade with that exact STL. Design operations never call printer transports.
- Public facade: `bambu_pipe.BambuPipeline`.
- Adapters: CLI, optional local REST API, and `voice2bambu`.
- Orchestrator: job state machine, approval gates, and printer queue.
- Stages: generate, validate, slice, and print.
- Providers: slicer, mesh generation, printer transport.

Adapters must not call printer or slicer internals directly. They create jobs and
drive approvals through the orchestrator.

CAD Python execution is trusted local code, not an HTTP upload provider. It runs
in a separate process with a timeout, without claiming to sandbox the source.
CAD/render dependencies are optional and imported lazily. The base package,
optional REST/voice adapters and Tripo provider keep their existing contracts.
The LLM runs in the user's agent harness; this package has no hidden inference
service or generation subscription.

The current printer capability is Bambu Lab A1 over LAN / Developer Mode. Future
device work should add explicit provider/capability contracts instead of
sprinkling model-specific conditionals through adapters. See
[`provider-contracts.md`](provider-contracts.md).

The optional REST API is a local adapter. Mutating routes are protected when
`BAMBU_PIPE_API_TOKEN` is set, and the CLI refuses non-loopback unauthenticated
binds unless the user passes `--i-understand-local-network-risk`.
