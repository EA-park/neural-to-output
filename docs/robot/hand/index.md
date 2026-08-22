# Hand

Documentation for mapping decoded commands to robot hand actuation.

## Registry and `RobotConfig`

Every concrete `RobotHand` registers itself under a name via `@register_hand("Name")`:

```python
from n2o.robot.hand import HAND_REGISTRY

HAND_REGISTRY  # {"AmazingHand": AmazingHand, "MockHand": MockHand}
```

`RobotConfig(hand="AmazingHand")` + `Robot.from_config(...)`/`make_robot(...)` resolve a name into an instance — see [Architecture → Building a robot from a `RobotConfig`](../../architecture.md#building-a-robot-from-a-robotconfig). This is additive: assigning an instance directly (`robot.hand = AmazingHand()`) always still works, and is the only option for ad hoc or simulated hands that were never registered.

Every concrete hand here besides `MockHand` is currently an interface-only stub (`raise NotImplementedError`).
