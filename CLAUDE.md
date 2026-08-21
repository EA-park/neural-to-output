# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A framework for driving robots from human electrophysiological signals (EEG/EMG). The pipeline is fixed: a `signal` source is decoded by a `decoder` into a command, which is sent to a `robot`'s `arm`/`hand`. See [examples/README.md](examples/README.md) for the intended usage shape.

## Commands

```bash
uv run pytest tests/test_n2o.py::test_main_runs  # run a single test
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the human-readable version — keep both in sync when this changes.

`src/n2o/` mirrors the pipeline as sibling packages, each following the same extension pattern — a `base.py` ABC plus one file per concrete implementation, re-exported from that package's `__init__.py`:

- `signal/dataset/` — signal sources (`EEG` non-invasive, `InvasiveEEG`, `EMG`)
- `decoder/` — signal → command decoders (`EEGNet`, `EMGDecoder`)
- `robot/arm/`, `robot/hand/` — actuators (`LeRobotSO101`, `Gello`, `MockArm`; `AmazingHand`, `MockHand`)

All concrete classes besides the `Mock*` ones are interface-only stubs (`raise NotImplementedError`) — no real hardware/model integration exists yet. `robot.Robot` is a plain container binding one `arm` + one `hand`; `N2O` (in `n2o/__init__.py`) wires a `signal` + `decoder` + `robot` together and its `.run()` drives one step of the pipeline.

To add a new dataset/decoder/robot: subclass the relevant `base.py` ABC in a new file next to the existing ones in that package, then re-export it from that package's `__init__.py` (walkthrough: [docs/tutorials/adding-a-component.md](docs/tutorials/adding-a-component.md)).

`mkdocs.yml`'s `nav:` is manually maintained and must stay in sync with `docs/` — `mkdocs build --strict` fails on orphaned pages or dangling nav entries.

Docs are bilingual (`mkdocs-static-i18n`, suffix mode): every `docs/<page>.md` needs a matching `docs/<page>.ko.md`. A missing `.ko.md` silently falls back to the English content in the `ko` build — `mkdocs build --strict` does **not** catch this, so check both files by hand when adding or editing a docs page.

`examples/` holds numbered, self-contained Jupyter notebooks (e.g. `examples/01_explore_eeg_decoder.ipynb`) — each notebook interleaves the explanation (markdown cells) with the runnable code, meant to be worked through in order. A `docs/tutorials/*.md` page may still exist for a notebook that needs a longer conceptual write-up or has no notebook yet; when it does pair with one, it links to the notebook rather than duplicating its explanation. See [examples/README.md](examples/README.md).

The `examples` dependency group (`uv sync --group examples`) pulls in the extra packages notebooks use (`jupyter`, `braindecode`, `moabb`, etc.) — these are not core `n2o` dependencies, so keep them out of `dependencies` / other groups.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (see [CONTRIBUTING.md](CONTRIBUTING.md)), e.g. `feat(robot): add Gello arm driver`.
