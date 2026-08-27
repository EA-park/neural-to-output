# Demos

Standalone applications built on top of `n2o`/the SO-101 hardware, as opposed to the
numbered tutorial notebooks in [`examples/`](../examples/README.md) — this is why these
have their own `demos` uv dependency group instead of using `examples`'s (which stays
scoped to what the tutorials need).

## `eeg_directional_arm_demo.py`

Loads real directional upper-limb EEG data ([Ofner2017][ofner2017], via
`braindecode`/`moabb`) — 7 classes: `right_elbow_flexion`, `right_elbow_extension`,
`right_supination`, `right_pronation`, `right_hand_open`, `right_hand_close`, `rest` —
trains a real EEGNet classifier (a genuine epoch-based training loop with held-out
validation accuracy, not a fixed-batch overfitting sanity check like `examples/04`/`06`,
or pretrained-checkpoint inference like `examples/03`), and drives the real SO-101 arm
through a pre-recorded pose per
predicted gesture, with a trapezoidal (accel/cruise/decel) velocity profile, via a small
local web UI.

[ofner2017]: https://doi.org/10.1371/journal.pone.0182578

### Prerequisites

Same hardware setup as `examples/09_real_so101_arm_control.ipynb` and
`examples/so101_control_panel.ipynb`:

```bash
uv sync --group demos
uv pip install -e /home/park/lerobot_robot_so101_5dof  # re-run after every `uv sync`
```

- The arm must already be calibrated (`uv run lerobot-calibrate
  --robot.type=so101_follower_5dof --robot.port=<port> --robot.id=n2o_so101_5dof` in a
  terminal — see `examples/09`'s intro for why this can't happen inside a Python
  process's own stdin).
- **`SO101GestureController`'s pose placeholders must be filled in first** (in
  `eeg_directional_arm_demo.py`): jog the real arm with
  `examples/so101_control_panel.ipynb` to a pose that visually reads as each gesture
  (e.g. `right_elbow_flexion` → arm visibly bending at the elbow), read off the 5 joint
  angles it displays, and type them into the matching method. Every method currently
  returns all-zero placeholders — the robot will just sit at its zero pose for every
  gesture until you do this.
- `hand` is `None` in every gesture method — there's no real gripper/hand connected yet
  (`n2o.robot.hand` stays `MockHand`, as in `examples/09`). Fill it in once one exists.

### Run

```bash
uv run --group demos python demos/eeg_directional_arm_demo.py
```

First run downloads Ofner2017 from Zenodo (~1GB, 10 runs × ~100MB for one subject's MI
session) and trains the classifier — this can take a while. Then open the printed
`http://127.0.0.1:5000` in a browser.

### Layout

- Top-left: the current trial's EEG waveform + scalp map (band power topomap).
- Bottom-left: an icon of the *predicted* gesture (drawn on the fly with matplotlib, no
  image assets needed), with Previous/Next buttons below it.
- Right: live joint-angle readout and a Moving/Idle status line.
- Top-right: **EMERGENCY STOP** — always clickable, even mid-motion. Hits `POST /stop`,
  which sets a `threading.Event` the motion loop checks every 20ms and aborts on —
  torque is deliberately *not* cut (that would let the arm fall under gravity, which is
  less safe than just holding the last commanded position).

Pressing Previous/Next: shows that trial's EEG/scalp map, runs the decoder, shows the
*predicted* gesture's icon (true label shown separately, in small text), and moves the
real arm to that gesture's pose along the trapezoidal profile. Both buttons disable
while the arm is moving.

### Safety limits

- `MAX_CARTESIAN_SPEED_M_S` / `MAX_CARTESIAN_ACCEL_M_S2` (top of the script, 1cm/s /
  0.5cm/s² by default) bound the trapezoidal profile — verified with
  `uv run --group demos python demos/verify_trapezoidal_profile.py`.
- `SO101Follower5DofConfig.max_relative_target` (2°) is a 2nd-order backstop, same role
  as in `examples/09`/`so101_control_panel`.
- Port is auto-detected by USB VID/PID (+ serial number, to disambiguate from a teleop
  leader arm using the same USB-serial chip) — no `lerobot-find-port` unplug/replug
  needed. Edit `SO101_USB_SERIAL_HINT` if your board's serial differs.

### Verifying without hardware

- `uv run --group demos python demos/verify_trapezoidal_profile.py` — numeric check that
  the motion profile never exceeds the configured speed/accel limits, for a range of
  distances.
- The Flask app's routing, threading, and emergency-stop-preempts-motion behavior were
  verified with a mock arm + mock decoder + `app.test_client()` (not checked in as a
  `tests/` pytest case, since that suite intentionally has no ML/robot dependencies —
  `demos/` is a separate dependency group for exactly that reason).
