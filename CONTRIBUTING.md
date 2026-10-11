# Contributing

Thanks for helping improve `bambu-pipe`.

You do not need a printer or an LLM API key for most contributions. Start with
[good first issues](https://github.com/aeshef/bambu-pipe/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
Each should contain a small scope, relevant files and concrete acceptance criteria.
Comment that you are working on an issue to avoid duplicate effort.

## Choose a development setup

Use Python 3.11 or 3.12 in a virtual environment. The base setup is enough for
CLI, API and most unit tests:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e 'packages/bambu_pipe[dev]'
```

For CAD or rendering changes, install `'packages/bambu_pipe[cad-dev]'` instead.
The CAD extra downloads native libraries; the first install is larger.
Windows activation is `.venv\Scripts\Activate.ps1` in PowerShell.
No printer, provider account or graphical CAD application is required.

## Make a focused pull request

Create a branch from current `main`; describe the concrete problem and resulting
behavior. Keep source changes, relevant tests and documentation together.
Screenshots must come from the actual exported geometry. Name the brief and
remaining assumptions. Label edited replays and deliberately seeded failures.

Before opening a PR:

1. Install dev dependencies with `pip install -e "packages/bambu_pipe[dev]"`.
2. Run `ruff check packages/bambu_pipe/src packages/voice2bambu/src tests apps examples`.
3. Run `ruff format --check packages/bambu_pipe/src packages/voice2bambu/src tests apps examples`.
4. Run `pytest -q`.
5. Run `python -m build packages/bambu_pipe` and `python -m build packages/voice2bambu`.
6. If you changed Docker files, run `docker build -f docker/Dockerfile.api .`.
7. Do not commit `.env`, generated models, sliced files, local profile exports, or
   reference clones.
8. Keep printer/slicer logic inside providers and stages, not adapters.

For CAD changes, run `pytest -q tests/cad tests/unit/test_design_contract.py`,
build an example and actually inspect all four PNGs. Do not claim physical
printing or another operating system was tested unless it was.

Generated STEP/STL, reports and videos belong in local `output/` or release
assets. Small reviewed preview images/GIFs may be committed under `docs/assets`
when their source and reproduction steps are included. Do not add large binary
files, fake testimonials, benchmark claims or unverified print guarantees.

Follow the [code of conduct](CODE_OF_CONDUCT.md). Report sensitive issues through
the private route in [SECURITY.md](SECURITY.md).

Hardware-dependent changes should include mocked tests and a short manual test
note describing printer model, material, and mode.

Security-sensitive changes should explain how they affect the local REST adapter,
printer LAN transport, FTPS/MQTT, file uploads, or provider API keys.
