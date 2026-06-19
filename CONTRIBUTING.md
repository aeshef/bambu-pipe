# Contributing

Thanks for helping improve `bambu-pipe`.

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

Hardware-dependent changes should include mocked tests and a short manual test
note describing printer model, material, and mode.

Security-sensitive changes should explain how they affect the local REST adapter,
printer LAN transport, FTPS/MQTT, file uploads, or provider API keys.
