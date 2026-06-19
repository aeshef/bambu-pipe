# PyPI Publishing Setup

This project should use PyPI Trusted Publishing. Do not create or share long-lived
PyPI API tokens.

## What The Maintainer Must Do

1. Create or log in to accounts:
   - <https://pypi.org/account/register/>
   - <https://test.pypi.org/account/register/>
2. Create/claim the `bambu-pipe` project name. If PyPI requires a first upload
   before settings are available, use TestPyPI first and keep the production
   project step for the release workflow.
3. In TestPyPI, open the project settings and add a Trusted Publisher:
   - Owner: `aeshef`
   - Repository: `bambu-pipe`
   - Workflow name: `publish.yml`
   - Environment name: `testpypi`
4. In PyPI, add the production Trusted Publisher:
   - Owner: `aeshef`
   - Repository: `bambu-pipe`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
5. In GitHub repository settings, create environments named `testpypi` and
   `pypi`. For `pypi`, require manual approval before deployment.
6. Send the repository maintainer confirmation only. Do not send passwords,
   recovery codes, or API tokens.

## Release Flow After Setup

1. Merge a release PR into `main`.
2. Create an annotated tag, for example `v0.2.0`.
3. Create a GitHub Release from the tag.
4. The publish workflow builds the package, verifies the wheel, and publishes to
   PyPI through Trusted Publishing.
5. Verify install from a clean environment:

```bash
python -m venv /tmp/bambu-pipe-install
/tmp/bambu-pipe-install/bin/python -m pip install bambu-pipe
/tmp/bambu-pipe-install/bin/bambu-pipe --help
```

## Package Names

Preferred production package name: `bambu-pipe`.

Fallback names if unavailable:

- `bambu-pipe-toolkit`
- `bambu-pipeline`
- `bambu-local-pipe`
