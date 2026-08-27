# Hand

Documentation for mapping a translated command to robot hand actuation.

## Registry and `RobotConfig`

Every concrete `RobotHand` registers itself under a name via `@register_hand("Name")`:

```python
from n2o.robot.hand import HAND_REGISTRY

HAND_REGISTRY  # {"AmazingHand": AmazingHand, "MockHand": MockHand}
```

`RobotConfig(hand="AmazingHand")` + `Robot.from_config(...)`/`make_robot(...)` resolve a
name into an instance — additive to direct attribute assignment (`robot.hand =
AmazingHand()`), same as [Arm](../arm/index.md#registry-and-robotconfig).

## Real hardware: `amazing_hand_real`

`AmazingHand` accepts an optional `controller: Controller`; `move()` delegates to
`self.controller.apply(decoder_type, command)`.
`src/n2o/robot/hand/amazing_hand_real/AmazingHandRealController` drives `rustypot`'s
`Scs0009PyController` directly (no high-level SDK calls exist for this hardware),
reusing the same `"grip"`/`"release"` action vocabulary the MuJoCo simulation uses —
real hardware and the sim share the joint convention, offset by each motor's own
bundled calibration constant:

```python
from n2o.robot.hand import AmazingHand
from n2o.robot.hand.amazing_hand_real import AmazingHandRealController

hand = AmazingHand(controller=AmazingHandRealController(serial_port="/dev/ttyACM0"))
```

Needs `rustypot` (the `examples`/`demos` dependency group), lazily imported. The
vendored upstream reference driver this was ported from lives in
[`third_party/AmazingHand/`](../../third-party/index.md) — not something this
controller imports at runtime, just what its calibration formula was checked against.

## Simulation

Driving a hand in simulation is `Robot`'s job, not `AmazingHand`'s -- see
[Robot → Visualizing with `Simulator`](../index.md#visualizing-with-simulator).
