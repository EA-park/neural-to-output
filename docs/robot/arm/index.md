# Arm

Documentation for mapping decoded commands to robot arm actuation.

## Registry and `RobotConfig`

Every concrete `RobotArm` registers itself under a name via `@register_arm("Name")`:

```python
from n2o.robot.arm import ARM_REGISTRY

ARM_REGISTRY  # {"LeRobotSO101": LeRobotSO101, "Gello": Gello, "MockArm": MockArm}
```

`RobotConfig(arm="LeRobotSO101")` + `Robot.from_config(...)`/`make_robot(...)` resolve a name into an instance — see [Architecture → Building a robot from a `RobotConfig`](../../architecture.md#building-a-robot-from-a-robotconfig). This is additive: assigning an instance directly (`robot.arm = LeRobotSO101()`) always still works, and is the only option for ad hoc or simulated arms that were never registered.

Every concrete arm here besides `MockArm` is currently an interface-only stub (`raise NotImplementedError`).
