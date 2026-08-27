# Examples

## Basic usage

```python
from n2o import N2O
from n2o.command import Command
from n2o.signal.dataset import DatasetLoader
from n2o.decoder import BraindecodeDecoder
from n2o.robot.arm import LeRobotSO101
from n2o.robot.hand import AmazingHand

n2o = N2O()
n2o.signal = DatasetLoader(path="path/to/recording")
n2o.decoder = BraindecodeDecoder("EEGNet", n_chans=59, n_outputs=4, n_times=100)
n2o.command = Command()
n2o.robot.arm = LeRobotSO101()
n2o.robot.hand = AmazingHand()
n2o.run()
```

`n2o.run()` reads one sample from `signal`, decodes it via `decoder`, translates that
prediction into per-part actions via `command`, and sends the result to both
`robot.arm` and `robot.hand`. Every `Decoder` must declare an `output_type`
(`FeatureType.ACTION` here) — see the Architecture section in
[CLAUDE.md](../CLAUDE.md) for how `FeatureType.LANGUAGE` routes differently.

### Building `robot` from a `RobotConfig`

The example above works for any component, including ad hoc or simulated ones that
were never registered — it always will. For named, reusable hardware, `robot.arm`/
`robot.hand`/`robot.camera` can also be built from a string name via a registry:

```python
from n2o.robot import Robot, RobotConfig

robot = Robot.from_config(RobotConfig(arm="LeRobotSO101", hand="AmazingHand"))
```

This is additive, not a replacement — it just makes swapping hardware a one-line
config change instead of an import + instantiation edit. See
[CLAUDE.md](../CLAUDE.md) for the full picture, including `RobotConfig.camera`/`.controller`.

## Built-in components

| Axis                  | Module              | Built-in classes                  |
| ---------------------- | -------------------- | ---------------------------------- |
| Signal dataset          | `n2o.signal.dataset` | `DatasetLoader` (concrete; `path=`/`name=`), ~150 moabb-backed libraries (via `name=`) |
| Signal stream           | `n2o.signal.stream`  | — (no concrete stream yet)         |
| Decoder                 | `n2o.decoder`         | `Classification`, `Regression` (task-type ABCs), `BraindecodeDecoder` |
| Command                 | `n2o.command`         | `Command` (usually subclassed per pipeline), `GripSpreadCommand` |
| Robot arm                | `n2o.robot.arm`       | `LeRobotSO101`, `Gello`, `MockArm` |
| Robot hand                | `n2o.robot.hand`      | `AmazingHand`, `MockHand`          |
| Robot camera              | `n2o.robot.camera`    | `MockCamera`                       |
| Controller                | `n2o.robot.language_controller` | `VLAController`           |

All of the above besides `MockArm`/`MockHand`/`MockCamera` are interface-only stubs for
now (no real hardware/model integration yet) — swap in the `Mock*` classes to exercise
the pipeline without physical hardware. More datasets, decoders, and robots will be
added over time, following the same pattern (see `CLAUDE.md`).

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
  the label to `robot.hand`, then wires it through `N2O` into `n2o.robot.hand.AmazingHand`.
  To actually *see* the hand move, it drives a MuJoCo simulation of the real
  [AmazingHand](https://github.com/pollen-robotics/AmazingHand) CAD model
  (`assets/amazing_hand_right/`, see that folder's `NOTICE.md` for provenance/license)
  instead of falling back to `MockHand`.
- **`05_finger_regression_amazinghand.ipynb`** — same shape, but for continuous output:
  a small regression `Decoder` (`config.type = DecoderType.REGRESSION`) predicts
  per-finger flexion (`{"finger1": 0.0-1.0, ...}`, matching `AmazingHand`'s real
  4-finger layout) from a synthetic EEG-like signal. Since those raw values aren't
  self-describing, `FingerFlexionCommand` tags them `(ActionType.JOINT_ABSOLUTE, {...})`
  before sending to `robot.hand` — contrast with `04`'s already-named `"grip"`/`"spread"`.
  Drives the same MuJoCo simulation as notebook 04 (flexion axis only; the abduction axis
  is held neutral).
- **`06_official_simulation_arm_and_hand.ipynb`** — drives both `n2o.robot.arm` and
  `n2o.robot.hand` together with a real `EEGNet` classifier on the same BCI IV 2a data
  as notebook 04, but keeps `Decoder`/`Command`/`Controller` cleanly separated: the
  decoder (`MotorImageryDecoder`) only outputs the dataset's raw label
  (`"left_hand"`/`"right_hand"`) — no robot awareness; `MotorImageryCommand.translate()`
  maps that label to a per-part action name (e.g. `{"arm": "up", "hand": "grip"}`); each
  robot part's own `n2o.robot.controller.Controller` turns that action name into actual
  motor targets. Simulated against each vendor's own official CAD-derived model — the
  SO-101 model from [`TheRobotStudio/SO-ARM100`](https://github.com/TheRobotStudio/SO-ARM100)
  (`assets/so101/`, the actual hardware/CAD repo behind `lerobot`'s `SO101Follower` —
  `lerobot` itself ships no simulation), and the same `assets/amazing_hand_right/` as
  notebooks 04/05, re-verified byte-for-byte against `pollen-robotics/AmazingHand`'s
  official output. Ends by checking every commanded arm joint against the vendored
  official range limits.
- **`07_regression_arm_and_hand.ipynb`** — `06`'s continuous counterpart: a regression
  `Decoder` predicts per-finger flexion (0-1) *and* real arm joint angles in radians
  (`shoulder_lift`, `elbow_flex`) — genuine per-joint regression, not a blend between
  two named poses. `ArmHandFlexionCommand` bundles the relevant keys per part and tags
  each `(ActionType.JOINT_ABSOLUTE, {...})`. Same `SO101ArmSim`/`AmazingHandSim`
  simulation and range-check as `06`.
- **`08_mixed_classification_regression.ipynb`** — one decoder wrapping two fully
  independent models (no shared trunk, separate optimizers/losses):
  `HandGestureClassifier` predicts the hand gesture (`config.type =
  (DecoderType.CLASSIFICATION, DecoderType.REGRESSION)`), and `ArmOffsetRegressor`
  predicts a small Cartesian *relative* step `(dx, dy)` (e.g. +0.5cm) rather than an
  absolute target. `MixedCommand` turns the class index into `"grip"`/`"release"` and
  tags the offset `(ActionType.CARTESIAN_RELATIVE, {...})`. The arm's `Controller`
  reads its *current* position live from the MuJoCo simulation state, adds the offset,
  and solves the result into `shoulder_pan`/`shoulder_lift`/`elbow_flex` joint angles
  with a small damped-least-squares inverse-kinematics loop against the vendored
  SO-101 model (clamped to its official joint ranges at every iteration), then drives
  the same MuJoCo simulation as `06`/`07`.
- **`09_real_so101_arm_control.ipynb`** — `08`'s `Decoder`/`Command` unchanged, but the
  arm side drives a **real** SO-101 follower (5 motors, ids 1-5, no gripper — a
  third-party hand goes where the stock gripper would) instead of the MuJoCo
  simulation: `SO101ArmRealController` reuses `08`'s damped-least-squares IK/range-clamp
  math verbatim, but reads "current position" from the real arm's `get_observation()`
  (via the local `lerobot_robot_so101_5dof` plugin — not on PyPI, see the notebook's
  intro cell for the one-time `uv pip install -e` step) instead of simulation state, and
  sends the resulting joint targets to the real motors in small ramped steps. Starts
  with a hardware bring-up section (connect/calibrate, read positions, one tiny
  single-joint move) before touching the `N2O` pipeline. The hand is still `MockHand` —
  no real gripper/hand is connected yet, so `n2o.robot.hand.AmazingHand` isn't
  exercised here.

Notebooks `04`-`08` demonstrate the full `signal -> decoder -> N2O -> robot.arm/hand` wiring
against the real `AmazingHand`/`LeRobotSO101` classes; since their `move()` are still
unimplemented stubs, each notebook falls back to a MuJoCo-simulated stand-in
(`AmazingHandSim`, `SO101ArmSim`) so you can watch the hand/arm actually move without real
hardware. `09` is the first exception — it sends real commands to a real arm; read its
safety notes before running it.

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
