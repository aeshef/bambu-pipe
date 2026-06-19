# Release Process

`main` should stay releasable. Use short-lived branches and pull requests for
all project changes.

## Branch Workflow

```bash
git checkout main
git pull
git checkout -b feat/small-change
```

Before opening a PR:

```bash
ruff check packages/bambu_pipe/src packages/voice2bambu/src apps tests examples
ruff format --check packages/bambu_pipe/src packages/voice2bambu/src apps tests examples
pytest -q
python -m build packages/bambu_pipe
python -m build packages/voice2bambu
```

Push and open a PR:

```bash
git push -u origin feat/small-change
gh pr create --fill
```

## Pull Request Rules

- Keep PRs focused and reviewable.
- CI must pass before merge.
- Do not commit `.env`, generated meshes, G-code, databases, caches, or local reference clones.
- Include manual printer smoke results when a change touches MQTT, FTPS, profiles, AMS, or slicing.

## Versioned Releases

For a patch release:

1. Update versions in package metadata.
2. Update `CHANGELOG.md`.
3. Merge the release PR into `main`.
4. Tag and push an annotated tag:

```bash
git tag -a v0.1.2 -m "bambu-pipe 0.1.2"
git push origin v0.1.2
```

5. Create a GitHub Release from the tag and include verification notes.

## Dependabot

Dependabot PRs should go through the same CI checks as human PRs. Merge them
when CI is green and the change is limited to dependency metadata or workflow
versions.
