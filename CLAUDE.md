# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A framework for driving robots from human electrophysiological signals (EEG/EMG). The pipeline is fixed: a `signal` source is decoded by a `decoder` into a raw prediction, which a `command` translates into per-part actions sent to a `robot`'s `arm`/`hand`/`camera`, or which is sent to a `controller` when the decoder's output is language-typed. See [examples/README.md](examples/README.md) for the intended usage shape.

## Commands

```bash
uv run pytest tests/test_n2o.py::test_main_runs  # run a single test
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for the human-readable version — keep both in sync when this changes.

`src/n2o/` mirrors the pipeline as sibling packages, each following the same extension pattern — a `base.py` ABC plus one file per concrete implementation, re-exported from that package's `__init__.py`:

- `signal/dataset/` — offline/indexed signal sources (`EEG` non-invasive, `InvasiveEEG`, `EMG`)
- `signal/stream/` — realtime/device signal sources (`EEGStream`, `EMGStream`), a sibling to `signal/dataset/` rather than a subclass of it (mirrors `mne.io.Raw` vs `mne_lsl.stream.StreamLSL`)
- `decoder/` — signal → raw prediction decoders (`EEGNet`, `EMGDecoder`)
- `command/` — translates a decoder's raw prediction into per-part actions (`Command`, `ActionType`, `CommandConfig`)
- `robot/arm/`, `robot/hand/`, `robot/camera/` — actuators/sensors (`LeRobotSO101`, `Gello`, `MockArm`; `AmazingHand`, `MockHand`; `MockCamera`)
- `controller/` — routes a `FeatureType.LANGUAGE`-typed command to a robot (`LanguageController`, concrete `VLAController`)

All concrete classes besides the `Mock*` ones are interface-only stubs (`raise NotImplementedError`) — no real hardware/model integration exists yet. `robot.Robot` is a plain container binding one `arm` + `hand` + `camera`; `N2O` (in `n2o/__init__.py`) wires a `signal` + `decoder` + `command` + `robot` + `controller` together. A `Decoder` instance is callable (`self.decoder(sample)` is shorthand for `.decode(sample)`); every `Decoder` subclass must declare an `output_type` ClassVar (`FeatureType.ACTION` or `FeatureType.LANGUAGE` — there is no other valid value, and `run()` raises `ValueError` if it's unset or anything else). `.run()` drives one step of the pipeline: `FeatureType.LANGUAGE` routes through `controller.act(decoded_signal, robot)`; `FeatureType.ACTION` routes through `command.translate(decoder, decoded_signal)`, which returns a dict with a `"type"` key (passed through from `decoder.config.type`) plus one key per robot part, dispatched as `robot.arm.move(actions["type"], actions["arm"])` / `robot.hand.move(actions["type"], actions["hand"])`.

`robot.arm`/`robot.hand`/`robot.camera`/`controller` can each also be built from a name via a registry: `@register_arm("Name")` (and the `hand`/`camera`/`controller` equivalents) register a class in a plain `dict`, and `RobotConfig(arm="LeRobotSO101", hand="AmazingHand", camera="MockCamera")` + `Robot.from_config(...)`/`make_robot(...)` resolve those names into instances. This is **additive** — direct attribute assignment (`robot.arm = SomeInstance()`) always still works, since ad hoc/simulated components are never registered.

`Command` (in `n2o/command/command.py`) is a plain overridable class, not a declarative config — its default `translate()` assumes `decoded_signal` is already keyed by robot part (`{"arm": ..., "hand": ...}`); subclass and override `translate(self, decoder, decoded_signal)` whenever a decoder's raw output needs real translation into that shape first. Each part's resulting value is either a bare, already self-describing name (e.g. `"grip"`) or an `(ActionType, value)` tuple for raw values that aren't self-describing on their own (e.g. a regression number/dict) — `ActionType` (`JOINT_ABSOLUTE`, `JOINT_RELATIVE`, `CARTESIAN_ABSOLUTE`, `CARTESIAN_RELATIVE`) travels with the value, independent of the decoder's own `DecoderType`. Keep a `Decoder` a plain predictor (raw prediction out) and put the prediction → per-part-action mapping in `Command`, not in the decoder — that's the whole reason `Command` exists.

`CommandConfig` (in `n2o/command/config.py`) is a separate, declarative contract for the `command` boundary — pairs with `Command` the same way `signal`/`decoder` pair `SignalConfig`/`DecoderConfig` with their runtime classes. There is no `N2O.verify()` method; call `n2o.command_config.verify_report(n2o)` directly (`n2o.command_config` is a plain attribute, set by the caller) to walk `signal -> decoder -> command -> robot.arm/hand` and print a match/mismatch/미정 table. `DecoderConfig.type` can be a `tuple[DecoderType, ...]` for a decoder wrapping more than one internal model (e.g. one classifier + one regressor with no shared trunk); `Command.translate()` reads `decoder.config.type` (an instance attribute, set in `__init__`, not a ClassVar) to decide how to interpret `decoded_signal`.

`n2o.robot.controller.Controller` (renamed from `MotorWrapper`) is a *different*, lower-level concept from `n2o.controller.LanguageController` despite the shared name — it's a per-robot-part dispatcher (`apply(decoder_type, action)`) that a `RobotArm`/`RobotHand` implementation owns and its `move(decoder_type, action)` typically delegates to, turning one action into a vendor SDK call or raw motor targets. Stays interface-only in `src/n2o/`; concrete vendor implementations are example/notebook-local.

To add a new dataset/stream/decoder/robot part: subclass the relevant `base.py` ABC in a new file next to the existing ones in that package, then re-export it from that package's `__init__.py` (walkthrough: [docs/tutorials/adding-a-component.md](docs/tutorials/adding-a-component.md)).

`mkdocs.yml`'s `nav:` is manually maintained and must stay in sync with `docs/` — `mkdocs build --strict` fails on orphaned pages or dangling nav entries.

Docs are bilingual (`mkdocs-static-i18n`, suffix mode): every `docs/<page>.md` needs a matching `docs/<page>.ko.md`. A missing `.ko.md` silently falls back to the English content in the `ko` build — `mkdocs build --strict` does **not** catch this, so check both files by hand when adding or editing a docs page.

`examples/` holds numbered, self-contained Jupyter notebooks (e.g. `examples/01_explore_eeg_decoder.ipynb`) — each notebook interleaves the explanation (markdown cells) with the runnable code, meant to be worked through in order. A `docs/tutorials/*.md` page may still exist for a notebook that needs a longer conceptual write-up or has no notebook yet; when it does pair with one, it links to the notebook rather than duplicating its explanation. See [examples/README.md](examples/README.md).

The `examples` dependency group (`uv sync --group examples`) pulls in the extra packages notebooks use (`jupyter`, `braindecode`, `moabb`, etc.) — these are not core `n2o` dependencies, so keep them out of `dependencies` / other groups.

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (see [CONTRIBUTING.md](CONTRIBUTING.md)), e.g. `feat(robot): add Gello arm driver`.
