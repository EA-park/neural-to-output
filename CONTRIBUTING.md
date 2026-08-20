# Contributing to neural-to-output

## Development setup

```bash
uv sync --group dev
```

## Running tests

```bash
uv run pytest
```

## Style

```bash
uv run ruff check .
uv run ruff format .
```

## Adding a dependency

New dependencies must not be GPL/AGPL/SSPL-licensed (incompatible with this project's Apache-2.0 license). Check with:

```bash
uv sync --group license
uv run pip-licenses --ignore-packages neural-to-output --fail-on="GPL;SSPL;Commons Clause;BUSL" --partial-match
```

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[(optional scope)]: <description>
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`, `style`.

Examples:

- `feat(robot): add Gello arm driver`
- `fix(ci): correct license-check dependency group`
- `docs: add Korean translation for architecture page`

## Pull requests

1. Fork the repo and create a branch off `main`.
2. Make your change, with tests where it makes sense.
3. Make sure `ruff check`, `ruff format --check`, `pytest`, and the license check all pass.
4. Open a PR describing what changed and why; the PR title should also follow Conventional Commits, since it becomes the commit message on merge.
