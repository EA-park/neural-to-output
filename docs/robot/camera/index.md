# Camera

Documentation for a robot-mounted camera used as a visual input for a `controller`.

## `RobotCamera`

`RobotCamera` (in `n2o.robot.camera`) is a base interface with a single abstract
method, `capture()`, returning the latest captured frame. It follows the same shape as
`RobotArm`/`RobotHand`: a `base.py` ABC, one file per concrete implementation, and
registration via `@register_camera("Name")`:

```python
from n2o.robot.camera import CAMERA_REGISTRY

CAMERA_REGISTRY  # {"MockCamera": MockCamera}
```

`RobotConfig(camera="MockCamera")` + `Robot.from_config(...)`/`make_robot(...)` resolve
a name into an instance, additive to direct attribute assignment (`robot.camera =
SomeInstance()`) — see
[Architecture → Building a robot from a `RobotConfig`](../../architecture.md#building-a-robot-from-a-robotconfig).

Only `MockCamera` exists today (prints instead of capturing); no real camera driver has
been added yet.
