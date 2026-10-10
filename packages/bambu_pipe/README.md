# bambu-pipe

Agent-assisted parametric CAD and local Bambu Lab print automation.

Install `bambu-pipe[cad]` on Python 3.11/3.12 for local CadQuery builds, STEP/STL,
four inspection views, measured geometry and revision-bound reviews. Run
`bambu-pipe design install-skill --target .agents/skills` to install the bundled
`bambu-design` skill for a terminal/vision agent. The CAD path needs no printer
credentials or generation API key. The agent uses its existing inference setup.

The base toolkit still provides mesh validation, local slicing, optional REST
and Tripo adapters, and Bambu A1 LAN printing. Design commands do not start prints.

See the [repository guide](https://github.com/aeshef/bambu-pipe#readme) for setup
and [design documentation](https://github.com/aeshef/bambu-pipe/blob/main/docs/design.md)
for acceptance contracts and limitations.
