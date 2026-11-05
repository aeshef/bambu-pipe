# Windows PowerShell CAD quickstart

> **Verification status — read this first.** This guide has **not** been run
> end to end on Windows PowerShell in this change: there was no Windows
> machine, PowerShell, CadQuery build, slicer, or Bambu printer available to
> the author. Every command below is translated from the project's existing
> Linux/macOS quickstart and from the CLI's own command definitions, and
> every link in this file was checked against the checkout. A Windows
> reviewer should run it once before treating it as verified, and should
> report back any step that differs. Do not claim a Windows CAD build, slice,
> or print was tested unless it actually was
> (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

This is the Windows PowerShell equivalent of the
[Quick start](../README.md#quick-start) in the README. It covers only the
local CAD loop: install, `design doctor`, the saved desk-hook reproduction,
visual review, and `verify`. Slicing and printing stay separate steps at the
end, and printing is never automatic.

## Prerequisites

- Windows 10 or 11 with PowerShell (Windows PowerShell 5.1, which ships with
  Windows, or PowerShell 7).
- Git for Windows.
- Python **3.11 or 3.12** for the CAD extra. Newer Python versions may lack
  CAD binary wheels. Install from python.org and make sure the
  `py` launcher is available; if typing `python` opens the Microsoft Store
  instead of printing a version, use `py -3.12` for every command below.
- No printer, slicer, LLM API key, GPU, or graphical CAD application is
  needed for the CAD loop itself. A slicer (OrcaSlicer or Bambu Studio) is
  needed only for the later slice stage, and a printer only for printing.

## 1. Clone and create the environment

```powershell
git clone https://github.com/aeshef/bambu-pipe.git
Set-Location bambu-pipe
py -3.12 --version
py -3.12 -m venv .venv
```

If `py` is not recognised, replace `py -3.12` with the full path to a
Python 3.11/3.12 `python.exe`, for example
`C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe`.

## 2. Activate the environment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The execution-policy line applies to the current PowerShell session only;
it is needed because Windows blocks running `Activate.ps1` under the
default `Restricted` policy. It does not change the system-wide policy.
From here on, `python` and `pip` refer to the virtual environment while
the prompt shows `(.venv)`. Run `deactivate` to leave it.

## 3. Install the CAD extra and check the toolchain

```powershell
pip install -e 'packages/bambu_pipe[cad]'
bambu-pipe design doctor
```

The quotes around the install target matter in PowerShell because of the
`[cad]` brackets. `design doctor` prints JSON listing Python and whether
`cadquery`, `matplotlib`, and `trimesh` are present; it exits with code 2
while any of them is missing, with the suggestion to use Python 3.11 or
3.12 and install `bambu-pipe[cad]`. No printer configuration is checked
by `design doctor`.

Install the agent skill for a terminal/vision agent you already have:

```powershell
bambu-pipe design install-skill --target .agents\skills
```

For another skill-capable agent, point `--target` at that agent's skills
folder instead (for example `.claude\skills`). The skill is copied
without overwriting an existing copy. The skill itself is documented in
[the design guide](design.md); a plain chat UI without file and terminal
access cannot execute this pipeline by itself.

## 4. Reproduce the saved desk-hook example

This rebuilds the [desk-edge hook](../examples/cad/desk-hook/brief.md) for
a 24 mm desk without an agent call, a printer, a slicer, or a paid service.
Dimensions are in millimetres; the expected print-oriented envelope is
80 × 65.5 × 35 mm.

```powershell
New-Item -ItemType Directory -Force -Path output\desk-hook | Out-Null
Copy-Item examples\cad\desk-hook\model.py, examples\cad\desk-hook\spec.json output\desk-hook\
bambu-pipe design build output\desk-hook
```

A successful build keeps, under `output\desk-hook\builds\<id>\`, the
source/spec snapshots, `model.step`, `model.stl`, four PNG views
(`isometric.png`, `front.png`, `right.png`, `top.png`), `preview.html`,
measurements, and checks. A failed build exits with code 2; read that
build's `worker.log`, fix the cause, and rebuild. Never reuse files from
an older successful build after a failure.

## 5. Inspect, review, and verify

Open all four PNGs from **this** build (for example with
`Invoke-Item output\desk-hook\builds\<id>\isometric.png`, and likewise for
`front.png`, `right.png`, and `top.png`) and compare them against the
brief: silhouettes, holes, walls, placement, and orientation. Green
geometry checks do not prove design intent.

Only after actually viewing all four, record the review:

```powershell
bambu-pipe design review output\desk-hook --decision accept --reviewer me `
  --view isometric.png --view front.png --view right.png --view top.png `
  --notes 'Two through holes and the web match the brief; fit still needs a test print.'
```

Then verify that the review still binds to the current inputs and
artifacts, and print the exact reviewed STL path as JSON:

```powershell
bambu-pipe design verify output\desk-hook
```

Any edit to the source, spec, model, images, or report invalidates the
review, so a changed workspace needs a new inspection and review before
it can be verified again.

## 6. Slice and print stay separate

Slicing needs a slicer and profiles; it never prints:

```powershell
bambu-pipe design slice output\desk-hook --material PLA --quality standard
```

`design slice` verifies the reviewed build first, then validates and
slices the verified STL for inspection. See
[printer setup](printer-setup.md) and the
[OrcaSlicer profiles](../profiles/README.md) (packaged Bambu Lab A1
defaults are used when no profiles directory is configured). The
physical print command is a separate, explicit step that uses FTPS and
MQTT with Bambu LAN / Developer Mode credentials; see
[printer setup](printer-setup.md) for the required `.env` settings
(printer IP, serial, and access code) and the TCP ports it checks
(`8883` for MQTT, `990` for FTPS). `bambu-pipe doctor` (without `design`)
is the check for printer, slicer, profiles, and staging; it is different
from `bambu-pipe design doctor`, which checks only the CAD toolchain.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the same PowerShell session, then activate again. |
| `py` is not recognised | Use the full path to a Python 3.11/3.12 `python.exe`, or reinstall Python from python.org with the launcher enabled. |
| Typing `python` opens the Microsoft Store | The Store stub is on `PATH` ahead of a real Python. Use `py -3.12` (or the full `python.exe` path) for the `venv` and install steps. |
| `design doctor` exits 2 with a CAD dependency missing | Confirm `python --version` inside the activated environment is 3.11 or 3.12, then reinstall with `pip install -e 'packages/bambu_pipe[cad]'`. The first CAD install downloads native libraries and is larger and slower than the base install. |
| `design build` exits 2 | Read that build's `worker.log` under `builds\<id>\`; a Python/CAD exception or a timeout is reported there, and a failed build removes the `latest` pointer. |
| `design verify` rejects a previously accepted build | Something changed after review (source, spec, model, image, or report). Re-inspect the four views of the current build and record a new review. |
| Slice fails with no slicer found | Install OrcaSlicer or Bambu Studio and, if auto-discovery fails, point the slicer binary or profiles directory at it as described in [printer setup](printer-setup.md). |
| Print fails before a job is created | The printer is not on the same LAN, LAN/Developer Mode is off, `.env` is incomplete, or ports `8883`/`990` are closed. Run `bambu-pipe doctor` and fix the reported check first. |

## See also

- [Quick start](../README.md#quick-start) — the Linux/macOS version of this guide.
- [Agent-assisted local CAD](design.md) — the spec contract, checks, and failure recovery.
- [Printer setup](printer-setup.md) — LAN/Developer Mode, `.env`, and ports.
- [OrcaSlicer profiles](../profiles/README.md) — exporting A1 machine, filament, and process profiles.
- [Contributing](../CONTRIBUTING.md) — development setup, including the one-line Windows activation note this guide expands.
