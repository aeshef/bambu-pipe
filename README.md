# bambu-pipe

[![CI](https://github.com/aeshef/bambu-pipe/actions/workflows/ci.yml/badge.svg)](https://github.com/aeshef/bambu-pipe/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Describe a part to your coding agent. Get editable CAD, measured geometry,
inspection views and a reviewed model. Slice and print locally when ready.**

The primary workflow uses a terminal/vision agent you already have and a local
CadQuery engine. The agent reasons about shape, writes parametric Python,
inspects four rendered views and iterates. The toolkit exports STEP/STL and
checks geometry independently of the agent's prose. No generation API key,
GPU, hosted backend or graphical CAD application is needed for this workflow.

Best for dimensioned parts: mounts, brackets, enclosures, organizers, adapters
and fixtures. Organic sculptures can still use the optional Tripo provider;
its generated mesh requires separate inspection and validation.

## Quick start

Use Python **3.11 or 3.12** for the CAD extra (newer Python versions may lack CAD
binary wheels). A slicer and printer are needed only for the later print stage.

```bash
git clone https://github.com/aeshef/bambu-pipe.git
cd bambu-pipe
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e 'packages/bambu_pipe[cad]'

bambu-pipe design doctor
bambu-pipe design install-skill --target .agents/skills
```

Open this folder in Codex and use `$bambu-design`, for example:

> Make a cable organizer 100 × 30 × 15 mm with five 6 mm channels. Use PLA,
> 2 mm walls and a flat base. Build it, inspect every view and give me editable
> CAD and STL. Ask if a dimension needed for fit is missing.

For another skill-capable terminal agent, install the same skill into its skills
folder, e.g. `--target .claude/skills`. Alternatively point an agent directly at
[SKILL.md](packages/bambu_pipe/src/bambu_pipe/skills/bambu-design/SKILL.md).
Your agent needs file/terminal access and image inspection. A plain chat UI
cannot execute this local pipeline by itself.

**Costs:** geometry, rendering and checks run locally. Agent inference uses
whatever subscription, API or local model your agent already uses. This package
neither bundles an LLM nor invokes a paid generation service in the CAD path.

## A reproducible design loop

```text
brief + dimensions → parameterized CAD → STEP/STL + four views
         ↑                  ↓
       revise ← mechanical checks + actual visual inspection
                            ↓
                  review bound to this build → local slice → print approval
```

You can also drive each step yourself:

```bash
# Creates a mounting-plate starter, NOT a model inferred from your brief.
bambu-pipe design init ./output/plate
# Adapt model.py and spec.json to your requirements.
bambu-pipe design build ./output/plate --json
# Open this build's isometric.png, front.png, right.png and top.png.
# Record a review only after inspecting them:
bambu-pipe design review ./output/plate --decision accept --reviewer me \
  --view isometric.png --view front.png --view right.png --view top.png \
  --notes 'Two through holes and the web match the brief; fit still needs a test print.'
bambu-pipe design verify ./output/plate
```

Every build keeps source/spec snapshots, `model.step`, `model.stl`, four PNGs,
`preview.html`, measurements and checks in `builds/<id>/`. A failed new build
invalidates the latest pointer. A changed source, spec, model, image or report
invalidates its review. `verify` prints the exact reviewed STL path as JSON.
`review` records a reviewer attestation; it is not a hidden visual LLM call.

Checks cover CAD validity, solid count, dimensions, bed fit, volume, Z=0
placement, material/void probes, mesh watertightness, winding and STL/CAD size
agreement. Point probes sample features; they do not prove every surface.
Wall thickness, strength, clearance, supports and real-world fit still need
CAD/slicer inspection and sometimes a test print. The validation score is a
heuristic, **not a probability of print success**.

Read [the design guide](docs/design.md) for the spec contract and failure recovery.

Try a complete [five-channel cable organizer](examples/cad/cable-organizer)
without any agent or provider call:

```bash
mkdir -p output/cable-organizer
cp examples/cad/cable-organizer/model.py examples/cad/cable-organizer/spec.json output/cable-organizer/
bambu-pipe design build output/cable-organizer
```

## Slice and print

Install OrcaSlicer or Bambu Studio and configure the correct profiles. See
[printer setup](docs/printer-setup.md) and [profiles](profiles/README.md).

```bash
# Verify the reviewed build, validate and slice it; no printer connection.
bambu-pipe design slice ./output/plate --material PLA --quality standard

# Other local meshes keep the existing CLI:
bambu-pipe validate --model ./model.stl
bambu-pipe preview --model ./model.stl --material PETG

# After inspecting the slice, use the verified STL path and explicitly start a print.
bambu-pipe print --model <verified-stl-path> --material PLA --yes
```

`design` never uploads or starts a print. The physical print command uses FTPS
and MQTT with Bambu A1 LAN / Developer Mode credentials. Configuration is only
needed at that stage; [`.env.example`](.env.example) lists supported settings.

## Existing integrations

The local toolkit remains usable independently of the CAD skill:

- `BambuPipeline` Python API: [documentation](docs/python-api.md).
- Optional FastAPI local adapter, SQLite jobs and uploads: [API](docs/api.md).
- Optional Telegram voice adapter: [voice2bambu](packages/voice2bambu/README.md).
- Tripo text-to-mesh: install `[tripo]`, configure the provider explicitly, then
  `bambu-pipe print 'small low-poly cat' --dry-run`. See [provider smoke test](docs/tripo-smoke.md).
- `doctor`, `status`, `jobs show`, `jobs artifacts`, `jobs retry` and existing
  mesh/slice/print approval stages remain available.

The REST API handles print jobs and meshes; CAD Python execution is a trusted
local CLI operation and is not exposed as a remote upload endpoint.

## Development

```bash
pip install -e 'packages/bambu_pipe[cad-dev]'
ruff check packages/bambu_pipe/src packages/voice2bambu/src tests apps examples
ruff format --check packages/bambu_pipe/src packages/voice2bambu/src tests apps examples
pytest -q
python -m build packages/bambu_pipe
```

CAD dependencies are optional. The base suite runs without them; the CAD suite
uses real OpenCascade builds and headless rendering when `[cad]` is installed.
CI runs both suites and checks that wheels include the skill.

[Architecture](docs/architecture.md) · [Configuration](docs/configuration.md) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) ·
[Issues](https://github.com/aeshef/bambu-pipe/issues)

MIT. Independent project, not affiliated with Bambu Lab.
