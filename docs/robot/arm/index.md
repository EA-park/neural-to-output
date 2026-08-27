# Arm

Documentation for mapping a translated command to robot arm actuation.

## Registry and `RobotConfig`

Every concrete `RobotArm` registers itself under a name via `@register_arm("Name")`:

```python
from n2o.robot.arm import ARM_REGISTRY

ARM_REGISTRY  # {"LeRobotSO101": LeRobotSO101, "Gello": Gello, "MockArm": MockArm}
```

`RobotConfig(arm="LeRobotSO101")` + `Robot.from_config(...)`/`make_robot(...)` resolve a
name into an instance — see
[Architecture → Building a robot from a `RobotConfig`](../../architecture.md#building-a-robot-from-a-robotconfig).
This is additive: assigning an instance directly (`robot.arm = LeRobotSO101()`) always
still works, and is the only option for ad hoc or simulated arms that were never
registered.

## `move()` and `Controller`

`LeRobotSO101` accepts an optional `controller: Controller`, and `move()` delegates
straight to `self.controller.apply(decoder_type, command)` — raising `RuntimeError`
(not `NotImplementedError`) if none was assigned. A `Controller` is a lower-level,
per-part dispatcher (`apply(decoder_type, action)`) that turns one action into a
vendor SDK call or raw motor targets — see [Controller](../../controller/index.md).

## Real hardware: `so101_real`

`src/n2o/robot/arm/so101_real/` is the real (non-simulated) SO-101 5-DOF driver:

- `lerobot_robot_so101_5dof/` — a verbatim vendored copy of a private local package's 3
  files, plain source rather than a pip/uv dependency.
- `connect_so101(port, **kwargs)` wraps constructing + connecting one.
- `SO101ArmRealController(Controller)` turns a gesture name or `(ActionType, {"dx",
  "dy"})` into a joint-degree target, then ramps every joint toward it speed-capped so
  no per-step delta exceeds `lerobot`'s own `max_relative_target` clamp.

```python
from n2o.robot.arm import LeRobotSO101
from n2o.robot.arm.so101_real import SO101ArmRealController

arm = LeRobotSO101(controller=SO101ArmRealController(port="/dev/ttyACM0"))
```

Needs `lerobot[feetech]` (the `examples`/`demos` dependency group), lazily imported.

## Simulation

`src/n2o/robot/simulation/` ships a bundled MuJoCo reference simulator —
`SO101ArmSim(RobotArm)`, backed by a real MJCF model. `N2O.run(simulation=True)` drives
it instead of `robot.arm`/`robot.hand`, lazily building and caching one per `N2O`
instance. `mujoco` is an `examples`/`demos`-group-only dependency — nothing under
`n2o.robot` imports `robot/simulation/` eagerly.
