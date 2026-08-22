# Examples

## Basic usage

```python
from n2o import N2O
from n2o.command import Command
from n2o.signal.dataset import EEG
from n2o.decoder import EEGNet
from n2o.robot.arm import LeRobotSO101
from n2o.robot.hand import AmazingHand

n2o = N2O()
n2o.signal = EEG()
n2o.decoder = EEGNet()
n2o.command = Command()
n2o.robot.arm = LeRobotSO101()
n2o.robot.hand = AmazingHand()
n2o.run()
```

`n2o.run()` reads one sample from `signal`, decodes it via `decoder`, translates that
prediction into per-part actions via `command`, and sends the result to both
`robot.arm` and `robot.hand`. Every `Decoder` must declare an `output_type`
(`FeatureType.ACTION` here) — see
[docs/architecture.md](../docs/architecture.md#routing-featuretype-and-languagecontroller).

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
[docs/architecture.md](../docs/architecture.md#building-a-robot-from-a-robotconfig)
for the full picture, including `RobotConfig.camera`/`.controller`.

## Built-in components

| Axis                  | Module              | Built-in classes                  |
| ---------------------- | -------------------- | ---------------------------------- |
| Signal dataset          | `n2o.signal.dataset` | `EEG` (non-invasive), `InvasiveEEG`, `EMG` |
| Signal stream           | `n2o.signal.stream`  | `EEGStream`, `EMGStream`           |
| Decoder                 | `n2o.decoder`         | `EEGNet`, `EMGDecoder`             |
| Command                 | `n2o.command`         | `Command` (subclass per pipeline) |
| Robot arm                | `n2o.robot.arm`       | `LeRobotSO101`, `Gello`, `MockArm` |
| Robot hand                | `n2o.robot.hand`      | `AmazingHand`, `MockHand`          |
| Robot camera              | `n2o.robot.camera`    | `MockCamera`                       |
| Controller                | `n2o.controller`      | `VLAController`                    |

All of the above besides `MockArm`/`MockHand`/`MockCamera` are interface-only stubs for
now (no real hardware/model integration yet) — swap in the `Mock*` classes to exercise
the pipeline without physical hardware. More datasets, decoders, and robots will be
added over time, following the same pattern (see `CLAUDE.md`).

## Numbered notebooks

This folder holds runnable, numbered Jupyter notebooks (`01_explore_eeg_decoder.ipynb`,
`02_...ipynb`, ...) meant to be worked through in order. Each notebook is
self-contained — markdown cells explain the concept right next to the code that runs
it — so there isn't always a separate write-up on the docs site; when a notebook does
need a longer conceptual walkthrough, that page lives under
[docs/tutorials/](../docs/tutorials/index.md) and links back to the notebook.

Install the extra packages notebooks need (not part of the core `n2o` dependencies)
with:

```bash
uv sync --group examples
uv run --group examples jupyter lab examples/01_explore_eeg_decoder.ipynb
```

- **`01_explore_eeg_decoder.ipynb`** — loads real EEG data (BCI Competition IV 2a via
  `braindecode`/`moabb`), walks through preprocessing, windowing, and the `EEGNet`
  decoder's actual input/output shapes — i.e. what `n2o.signal.dataset.EEG.read()` and
  `n2o.decoder.EEGNet.decode()` need to produce/consume once they're implemented for
  real.
- **`02_hand_intent_classification_amazinghand.ipynb`** — subclasses `n2o.decoder.Decoder`
  around an `EEGNet` classifier (`output_type = FeatureType.ACTION`,
  `config.type = DecoderType.CLASSIFICATION`) to turn EEG windows into a raw
  `"grip" | "spread"` label (reusing the same BCI IV 2a data as notebook 01, with
  `left_hand`/`right_hand` as a grip/spread stand-in), a `GripSpreadCommand` that routes
  the label to `robot.hand`, then wires it through `N2O` into `n2o.robot.hand.AmazingHand`.
  To actually *see* the hand move, it drives a MuJoCo simulation of the real
  [AmazingHand](https://github.com/pollen-robotics/AmazingHand) CAD model
  (`assets/amazing_hand_right/`, see that folder's `NOTICE.md` for provenance/license)
  instead of falling back to `MockHand`.
- **`03_finger_regression_amazinghand.ipynb`** — same shape, but for continuous output:
  a small regression `Decoder` (`config.type = DecoderType.REGRESSION`) predicts
  per-finger flexion (`{"finger1": 0.0-1.0, ...}`, matching `AmazingHand`'s real
  4-finger layout) from a synthetic EEG-like signal. Since those raw values aren't
  self-describing, `FingerFlexionCommand` tags them `(ActionType.JOINT_ABSOLUTE, {...})`
  before sending to `robot.hand` — contrast with `02`'s already-named `"grip"`/`"spread"`.
  Drives the same MuJoCo simulation as notebook 02 (flexion axis only; the abduction axis
  is held neutral).
- **`04_official_simulation_arm_and_hand.ipynb`** — drives both `n2o.robot.arm` and
  `n2o.robot.hand` together with a real `EEGNet` classifier on the same BCI IV 2a data
  as notebook 02, but keeps `Decoder`/`Command`/`Controller` cleanly separated: the
  decoder (`MotorImageryDecoder`) only outputs the dataset's raw label
  (`"left_hand"`/`"right_hand"`) — no robot awareness; `MotorImageryCommand.translate()`
  maps that label to a per-part action name (e.g. `{"arm": "up", "hand": "grip"}`); each
  robot part's own `n2o.robot.controller.Controller` turns that action name into actual
  motor targets. Simulated against each vendor's own official CAD-derived model — the
  SO-101 model from [`TheRobotStudio/SO-ARM100`](https://github.com/TheRobotStudio/SO-ARM100)
  (`assets/so101/`, the actual hardware/CAD repo behind `lerobot`'s `SO101Follower` —
  `lerobot` itself ships no simulation), and the same `assets/amazing_hand_right/` as
  notebooks 02/03, re-verified byte-for-byte against `pollen-robotics/AmazingHand`'s
  official output. Ends by checking every commanded arm joint against the vendored
  official range limits.
- **`05_regression_arm_and_hand.ipynb`** — `04`'s continuous counterpart: a regression
  `Decoder` predicts per-finger flexion (0-1) *and* real arm joint angles in radians
  (`shoulder_lift`, `elbow_flex`) — genuine per-joint regression, not a blend between
  two named poses. `ArmHandFlexionCommand` bundles the relevant keys per part and tags
  each `(ActionType.JOINT_ABSOLUTE, {...})`. Same `SO101ArmSim`/`AmazingHandSim`
  simulation and range-check as `04`.
- **`06_mixed_classification_regression.ipynb`** — one decoder wrapping two fully
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
  the same MuJoCo simulation as `04`/`05`.

Notebooks `02`-`06` demonstrate the full `signal -> decoder -> N2O -> robot.arm/hand` wiring
against the real `AmazingHand`/`LeRobotSO101` classes; since their `move()` are still
unimplemented stubs, each notebook falls back to a MuJoCo-simulated stand-in
(`AmazingHandSim`, `SO101ArmSim`) so you can watch the hand/arm actually move without real
hardware.
