# Contributing

Thanks for helping! Protoreel aims to stay small and readable, so a new contributor can
understand any file in one sitting.

## Set up

```bash
git clone https://github.com/iamkingsleey/protoreel && cd protoreel
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python -m playwright install chromium
pytest
```

## House rules

- **Name things for what they mean** to someone making videos (`take`, `frame`, `format`), not how they're implemented.
- **One job per module.** If a file starts doing two things, split it. [docs/architecture.md](docs/architecture.md) is the map; update it when the map changes.
- **Explain why, not what,** in comments. Short docstrings on every public function.
- **Readable errors.** Anything a user can fix should say what went wrong and what to do.
- `ruff check` and `ruff format` before you push; CI runs both, plus the tests.

## Making a release

1. Bump `__version__` in `src/protoreel/__init__.py` and add a section to `CHANGELOG.md`.
2. Commit, then tag: `git tag v0.2.0 && git push --tags`.
3. The *Release* workflow builds the package and publishes it to PyPI.
