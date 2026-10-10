# Working on bambu-pipe

For designing printable parts, read
`packages/bambu_pipe/src/bambu_pipe/skills/bambu-design/SKILL.md`.
It describes a local build/inspect/revise workflow for a terminal and vision agent.
The canonical skill lives in the Python package so wheel installs can copy it
with `bambu-pipe design install-skill --target <skills-directory>`.

For software changes, keep CAD dependencies optional and CLI/API adapters thin.
`design` operations must work without printer credentials or LLM API keys.
`design slice` must verify review evidence before using the existing slice pipeline
and must never contact the printer. Do not replace executable geometry checks
with language-model assertions or interpret heuristic scores as probabilities.

Verify with Ruff, pytest and wheel builds. With the CAD extra installed, also run
the real CAD tests and inspect an example's rendered PNGs. Tests must not start a
physical print or invoke paid generation services.
