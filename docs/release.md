# Release Plan

`ra-library` releases are retained on GitHub. The release workflow builds wheel
and source artifacts but does not publish them to PyPI or another registry.

## Repository Cleanup Policy

- Do not commit generated distributions from `dist/`.
- Do not commit virtual environments, test caches, lint caches, or coverage files.
- Keep only source files and intended runtime data under `src/ra_library/data/`.
- Keep the README install command aligned with the current GitHub tag.
- Run the local checks before tagging a release.

## Local Checks

```bash
uv sync --group dev
uv run pre-commit run --all-files
uv run pytest -q
uv run python -m build --sdist --wheel
uv run twine check dist/*
```

Install hooks once per checkout:

```bash
uv run pre-commit install
```

## Tag-Only Release Flow

1. Update `project.version` in `pyproject.toml`.
2. Update `src/ra_library/__init__.py` if `__version__` changes.
3. Run the local checks.
4. Commit the release changes and push `main`.
5. Create and push a matching tag:

```bash
git tag -a v0.4.0 -m "ra-library v0.4.0"
git push origin v0.4.0
```

The release workflow only runs on tags matching `v*`. It verifies that the
tag exactly matches `project.version`, runs tests, builds fresh distributions,
checks them with Twine, and attaches them to a GitHub Release.
