# Hand

Documentation for `n2o.robot.hand`'s concrete driver.

## `AmazingHand`

[`AmazingHand`][n2o.robot.hand.amazing_hand_right.AmazingHand] is the shipped
[`Part`](../index.md#the-part-interface) for the AmazingHand right-hand gripper —
`goal(cmd)` looks up `cmd` in `GESTURES` (9 named poses, pure computation, no I/O),
`move(cmd)` lazily connects to the real `rustypot` servo SDK (first call, torque-
enabling every motor), then sends each motor's gesture value plus its own bundled
calibration offset, clamped to a hardcoded safe range (the vendor SDK has none of
its own). `disconnect()` torque-disables every motor.

```python
from n2o.robot.hand import AmazingHand

hand = AmazingHand(port="/dev/ttyACM0")
hand.move("grip")
hand.disconnect()
```

Needs `rustypot` (the `examples`/`demos` dependency group), lazily imported —
building/using `AmazingHand` for `goal()` only never needs it installed.

## Why `_right`

The bundled CAD and per-motor calibration are for the right-hand CAD variant
specifically (see `NOTICE.md`) — a left-hand variant, if one is added later, would
be a sibling package (`amazing_hand_left/`), not a flag on this one, since the
calibration constants themselves are unit/hand-specific.

The vendored upstream reference driver this was ported from lives in
[`third_party/AmazingHand/`](../../third-party/index.md) — not something
`AmazingHand` imports at runtime, just what its calibration formula was checked
against.

## Simulation

Driving a hand in simulation is `Robot`'s job, not `AmazingHand`'s — see
[Robot → Visualizing with `Simulator`](../index.md#visualizing-with-simulator). The
bundled MJCF/Unity assets live alongside the driver code in
`hand/amazing_hand_right/` (`mjcf/`, `unity_model/`) — see that folder's
`NOTICE.md` for CAD provenance
([`pollen-robotics/AmazingHand`](https://github.com/pollen-robotics/AmazingHand)).
