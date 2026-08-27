# Examples

## Basic usage

```python
from n2o import N2O
from n2o.command import Command
from n2o.signal.dataset import DatasetLoader
from n2o.decoder import BraindecodeDecoder
from n2o.robot.arm.so101 import SO101Arm
from n2o.robot.hand.amazing_hand import AmazingHand

n2o = N2O()
n2o.signal = DatasetLoader(path="path/to/recording")
n2o.decoder = BraindecodeDecoder("EEGNet", n_chans=59, n_outputs=4, n_times=100)
n2o.command = Command()
n2o.robot.arm = SO101Arm(port="/dev/ttyACM0")
n2o.robot.hand = AmazingHand(port="/dev/ttyACM1")
n2o.run()
```

`n2o.run()` reads one sample from `signal`, decodes it via `decoder`, translates that
prediction into per-part actions via `command`, and routes the result to whichever of
`robot.arm`/`robot.hand` the command actually targets, via `robot.router()`. Every
`Decoder` must declare an `output_type` (`FeatureType.ACTION` here) — see the
Architecture section in [CLAUDE.md](../CLAUDE.md) for how `FeatureType.LANGUAGE`
routes differently.

`n2o.run()` defaults to driving real hardware (`controller="motor_driver"`). Pass
`n2o.run(controller="simulation")` instead to visualize each command's target in
MuJoCo (via `n2o.robot.simulation.Simulator`) without touching real hardware — see
notebooks `04`-`08` below, and [the Robot docs](../docs/robot/index.md#visualizing-with-simulator).

## Built-in components

| Axis                  | Module              | Built-in classes                  |
| ---------------------- | -------------------- | ---------------------------------- |
| Signal dataset          | `n2o.signal.dataset` | `DatasetLoader` (concrete; `path=`/`name=`), ~150 moabb-backed libraries (via `name=`) |
| Signal stream           | `n2o.signal.stream`  | — (no concrete stream yet)         |
| Decoder                 | `n2o.decoder`         | `Classification`, `Regression` (task-type ABCs), `BraindecodeDecoder` |
| Command                 | `n2o.command`         | `Command` (usually subclassed per pipeline), `GripSpreadCommand` |
| Robot arm                | `n2o.robot.arm.so101` | `SO101Arm`                          |
| Robot hand                | `n2o.robot.hand.amazing_hand` | `AmazingHand`               |
| Robot camera              | `n2o.robot.camera`    | — (empty placeholder, not implemented yet) |
| Simulation                | `n2o.robot.simulation` | `Simulator` (MuJoCo, opt-in via `robot.simulator`) |

There's one concrete implementation per part (no registry/mock classes) — assign an
instance directly (`n2o.robot.hand = AmazingHand(port=...)`). Both `SO101Arm`/
`AmazingHand` own their real hardware connection directly (lazily, on first `move()`
call), and expose `goal(cmd)` (pure target computation, no I/O) alongside `move(cmd)`
(drives the real hardware) — see [the Robot docs](../docs/robot/index.md) for the
full `Part`/`ControllerType`/`Robot.router()` picture. More datasets, decoders, and
robot parts will be added over time (see `ROADMAP.md`).

## Numbered notebooks

This folder holds runnable, numbered Jupyter notebooks (`01_explore_eeg_dataset.ipynb`,
`02_...ipynb`, ...) meant to be worked through in order. Each notebook is
self-contained — markdown cells explain the concept right next to the code that runs
it, so this is the sole source of tutorial-style documentation for the project (there
is no separate docs site).

Install the extra packages notebooks need beyond core `n2o` (`moabb`/`braindecode`
themselves are core dependencies now — see [CLAUDE.md](../CLAUDE.md) — this group is
just `jupyter` + the robot/simulation stack) with:

```bash
uv sync --group examples
uv run --group examples jupyter lab examples/01_explore_eeg_dataset.ipynb
```

- **`01_explore_eeg_dataset.ipynb`** — browses `n2o.signal.dataset.DatasetLoader`'s
  registered library (`list_libraries()`/`library_tree()`, ~150 entries, almost all
  moabb-backed), checks a specific one's metadata (`DatasetLoader(...).info()` — origin,
  cue-relative data range, channel count), then calls `DatasetLoader(name=...).read()`
  (BCI Competition IV 2a, `BNCI2014_001`) for the raw recording and
  `n2o.decoder.bandpass_standardize()`/`.window_by_event()` stepwise on top of it to see
  what preprocessing and event-based windowing each actually change — turning a raw
  recording into decoder-ready windows is `n2o.decoder`'s job now, not the signal
  source's, so `read()` itself only loads.
- **`02_add_custom_dataset.ipynb`** — moabb doesn't have every dataset; for a local
  recording (`path=` instead of `name=`), `DatasetLoader(path=...)` requires a
  `dataset_info.py` metadata file to already exist in the folder — it refuses to
  construct otherwise. Walks through generating one with `write_metadata_template()`
  (in a scratch location, deliberately separate from the recording folder), filling it
  in, moving it into the recording folder, and only then constructing `DatasetLoader`.
- **`03_explore_eegnet_decoder.ipynb`** — the same BCI IV 2a data as notebook 01
  (`DatasetLoader.read()` + `n2o.decoder`'s `bandpass_standardize()`/`window_by_event()`),
  now through `n2o.decoder.BraindecodeDecoder`'s `EEGNet`: its actual input/output
  shapes. This project doesn't train a decoder, so
  instead of a training loop, it downloads a real pretrained checkpoint (braindecode's
  own official `ShallowFBCSPNet`, hosted on Hugging Face) and runs genuine inference on
  held-out data — real accuracy, no training required.
- **`04_hand_intent_classification_amazinghand.ipynb`** — subclasses `n2o.decoder.Decoder`
  around an `EEGNet` classifier (`output_type = FeatureType.ACTION`,
  `config.type = DecoderType.CLASSIFICATION`) to turn EEG windows into a raw
  `"grip" | "spread"` label (reusing the same BCI IV 2a data as notebooks 01/03, with
  `left_hand`/`right_hand` as a grip/spread stand-in), a `GripSpreadCommand` that routes
  the label to `robot.hand`, then wires it through `N2O` into a real
  `n2o.robot.hand.amazing_hand.AmazingHand`. To *see* the hand move without real
  hardware, it calls `n2o.run(controller="simulation")`, which visualizes each
  `goal()` target against the real
  [AmazingHand](https://github.com/pollen-robotics/AmazingHand) CAD model
  (`assets/amazing_hand_right/`, see that folder's `NOTICE.md` for provenance/license)
  via `n2o.robot.simulation.Simulator`.
- **`05_finger_regression_amazinghand.ipynb`** — same shape, but for continuous output:
  a small regression `Decoder` (`config.type = DecoderType.REGRESSION`) predicts
  per-finger flexion from a synthetic EEG-like signal, tagged
  `(ActionType.JOINT_ABSOLUTE, {...})` before sending to `robot.hand` — contrast with
  `04`'s already-named `"grip"`/`"spread"`. Same `controller="simulation"`
  visualization as notebook 04.
- **`06_official_simulation_arm_and_hand.ipynb`** — drives both `n2o.robot.arm` and
  `n2o.robot.hand` together with a real `EEGNet` classifier on the same BCI IV 2a data
  as notebook 04, and keeps `Decoder`/`Command`/`Robot` cleanly separated: the decoder
  (`MotorImageryDecoder`) only outputs the dataset's raw label (`"left_hand"`/
  `"right_hand"`) — no robot awareness; `MotorImageryCommand.translate()` maps that
  label to a per-part action name (e.g. `{"arm": "up", "hand": "grip"}`); `SO101Arm`/
  `AmazingHand` (both real `n2o.robot.Part` implementations) turn an action name into
  a target via `goal()`, and `n2o.robot.simulation.Simulator` visualizes it against
  each vendor's own official CAD-derived model — the SO-101 model from
  [`TheRobotStudio/SO-ARM100`](https://github.com/TheRobotStudio/SO-ARM100)
  (`assets/so101/`, the actual hardware/CAD repo behind `lerobot`'s `SO101Follower` —
  `lerobot` itself ships no simulation), and the same `assets/amazing_hand_right/` as
  notebooks 04/05, re-verified byte-for-byte against `pollen-robotics/AmazingHand`'s
  official output.
- **`07_regression_arm_and_hand.ipynb`** — `06`'s continuous counterpart: a regression
  `Decoder` predicts per-finger flexion (0-1) *and* real arm joint angles in radians
  (`shoulder_lift`, `elbow_flex`) — genuine per-joint regression, not a blend between
  two named poses. `ArmHandFlexionCommand` bundles the relevant keys per part and tags
  each `(ActionType.JOINT_ABSOLUTE, {...})`. Same `Simulator` visualization as `06`.
- **`08_mixed_classification_regression.ipynb`** — one decoder wrapping two fully
  independent models (no shared trunk, separate optimizers/losses):
  `HandGestureClassifier` predicts the hand gesture (`config.type =
  (DecoderType.CLASSIFICATION, DecoderType.REGRESSION)`), and `ArmOffsetRegressor`
  predicts a small Cartesian *relative* step `(dx, dy)` (e.g. +0.5cm) rather than an
  absolute target. `SO101Arm` doesn't have a Cartesian gesture yet (only named
  `"up"`/`"down"` — see `ROADMAP.md`), so this notebook calls
  `n2o.robot.arm.lerobot_robot_so101_5dof.solver.SO101IKSolver` directly: it solves
  the offset (against the arm's last known joint state) into
  `shoulder_pan`/`shoulder_lift`/`elbow_flex` angles with a damped-least-squares
  inverse-kinematics loop, clamped to the vendored SO-101 model's official joint
  ranges, then hands the result to `Simulator.drive("arm", target_deg)` directly for
  visualization.
- **`09_real_so101_arm_control.ipynb`** — `08`'s `Decoder`/`Command` unchanged, but the
  arm side drives a **real** SO-101 follower (5 motors, ids 1-5, no gripper — a
  third-party hand goes where the stock gripper would) via a real
  `n2o.robot.arm.so101.SO101Arm(port=...)` instead of the MuJoCo simulation — the
  named `"up"`/`"down"` gestures only (the notebook's Cartesian/IK exploration cells
  call `SO101IKSolver` directly, same as `08`, decoupled from live arm driving since
  that path isn't wired into `SO101Arm` yet). Starts with a hardware bring-up section
  (connect/calibrate, read positions, one tiny single-joint move) before touching the
  `N2O` pipeline. `robot.hand` is left unset — no real gripper/hand is connected yet,
  so `AmazingHand` isn't exercised here.

Notebooks `04`-`08` demonstrate the full `signal -> decoder -> N2O -> robot.arm/hand`
wiring against the real `SO101Arm`/`AmazingHand` classes, visualized via
`n2o.run(controller="simulation")` so you can watch the hand/arm move without real
hardware. `09` is the first exception — it sends real commands to a real arm; read its
safety notes before running it.

- **`10_py_trees_task_coordination.ipynb`** — a detour from the decoder pipeline into
  robot-side task coordination: `Robot.router()` (`src/n2o/robot/__init__.py`) only
  dispatches every part named in one translated command as a flat, one-shot parallel
  batch — it has no way to express ordering between parts, fallback on failure, or
  sequencing across more than one `Robot()` instance. This notebook learns
  [`py_trees`](https://github.com/splintered-reality/py_trees) (`Sequence`/
  `Selector`/`Parallel`, `Behaviour.update()` returning `RUNNING`/`SUCCESS`/`FAILURE`)
  against the real `SO101Arm`/`AmazingHand` `Part`s as a candidate for that gap —
  `goal()` (pure, no I/O) for simple ordering/fallback examples, then `Part.done_event`
  (the hook `Robot.router()` already sets/clears per dispatch, meant for a future
  cross-part coordinator — see `ROADMAP.md`) polled from a custom `Behaviour` to show
  multi-tick `RUNNING` coordination, including across two independent `Robot()`
  instances ("stations") sequenced one after another. Exploratory only — `Robot.router()`/
  `N2O.run()` are untouched. `py_trees` is now an `examples`-group-only dependency
  (`pyproject.toml`), added for this notebook.

## Hardware utilities (not part of the numbered series)

- **`so101_control_panel.ipynb`** — a standalone `ipywidgets` control panel for the real
  SO-101 follower from `09`, independent of the `Decoder`/`Command`/`N2O` pipeline: auto-detects
  its serial port by USB VID/PID (+ serial number, to disambiguate from a teleop leader arm using
  the same chip) instead of `lerobot-find-port`'s unplug/replug flow, plus buttons for
  connect/disconnect and torque on/off, per-joint min/max range fields (can only narrow the
  official range, never widen it), a live movement-speed cap (°/s), and per-joint sliders that
  drive the real arm as you drag them, rate-limited to that speed cap. Same prerequisites as `09`
  (`lerobot[feetech]` + the local `lerobot_robot_so101_5dof` plugin, and calibration done via
  `lerobot-calibrate` in a terminal first).
