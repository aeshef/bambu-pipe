# Contributing

Thanks for helping improve `bambu-pipe`.

Before opening a PR:

1. Run `ruff check packages/bambu_pipe/src tests apps scripts`.
2. Run `pytest`.
3. Do not commit `.env`, generated models, sliced files, local profile exports, or
   reference clones.
4. Keep printer/slicer logic inside providers and stages, not adapters.

Hardware-dependent changes should include mocked tests and a short manual test
note describing printer model, material, and mode.
