# Getting Started

See [Installation](installation.md) to set up the project locally.

## Dependency groups

Only `braindecode`/`moabb` are core dependencies (`pyproject.toml`'s
`project.dependencies`) — everything else is behind a `uv` dependency group, installed
with `uv sync --group <name>`:

| Group      | What it's for                                                              |
| ---------- | --------------------------------------------------------------------------- |
| `dev`      | `pytest`, `ruff` — running the test suite and linting                       |
| `license`  | `pip-licenses` — see [`sbom.md`](https://github.com/EA-park/neural-to-output/blob/main/sbom.md) |
| `docs`     | `mkdocs`, `mkdocs-material`, `mkdocs-static-i18n` — this site                |
| `examples` | `jupyter`, `mujoco`, `lerobot`, `rustypot`, `torchaudio` — the tutorial notebooks and robot simulation/hardware drivers |
| `demos`    | `examples`'s stack plus `flask` — standalone applications under `demos/`     |

`uv sync --all-groups` pulls in everything at once (useful for CI-parity checks, but
slow — `torch`/`mujoco`/`lerobot` are large).

## Running the numbered tutorials

```bash
uv sync --group examples
uv run jupyter lab examples/
```

Work through `examples/01_explore_eeg_dataset.ipynb` onward — see
[`examples/README.md`](https://github.com/EA-park/neural-to-output/blob/main/examples/README.md)
for the full list and intended order.

## Running the test suite

```bash
uv sync --group dev
uv run pytest
```

## Working on this site

Install the `docs` dependency group and serve locally with live reload:

```bash
uv sync --group docs
uv run mkdocs serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).
