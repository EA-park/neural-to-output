# Arm

Documentation for `n2o.robot.arm`'s concrete driver.

## `SO101Arm`

[`SO101Arm`][n2o.robot.arm.so101.SO101Arm] is the shipped [`Part`](../index.md#the-part-interface)
for the SO-101 5-DOF arm — `goal(cmd)` looks up `cmd` in `GESTURES` (`"up"`/`"down"`,
pure computation, no I/O), `move(cmd)` lazily connects to the real hardware (first
call) then ramps only the `shoulder_pan` joint toward the target in joint-degree
space, speed-capped (`MAX_JOINT_SPEED_DEG_S`) so no per-step delta exceeds
`lerobot`'s own `max_relative_target` clamp.

```python
from n2o.robot.arm import SO101Arm

arm = SO101Arm(port="/dev/ttyACM0")
arm.move("up")
```

## Real hardware: the vendored `lerobot_robot_so101_5dof/` driver

This SO-101 build is a 5-motor configuration (no gripper) that `lerobot`'s stock
6-motor SO-101 class doesn't support, so `SO101Arm` connects through
`src/n2o/robot/arm/so101/lerobot_robot_so101_5dof/` instead — a verbatim vendored
copy of a private local package's 3 files (`SO101Follower5Dof`/
`SO101Follower5DofConfig`, a `lerobot`-framework `Robot`/`RobotConfig`, not an
`n2o.robot.Part`), plain source rather than a pip/uv dependency. Needs
`lerobot[feetech]` (the `examples`/`demos` dependency group), lazily imported —
building/using `SO101Arm` for `goal()` only never needs it installed.

If no calibration file exists yet for the given `id`, `move()` raises a
`RuntimeError` pointing at the one-off terminal commands needed to create one
(`so101_follower_5dof` isn't a registered `lerobot` robot type, so the plain
`lerobot-calibrate` CLI can't build it directly).

## Cartesian IK: `SO101IKSolver`

[`SO101IKSolver`][n2o.robot.arm.so101.lerobot_robot_so101_5dof.solver.SO101IKSolver]
is pure Cartesian-offset IK (damped least squares against the bundled MJCF model) —
no hardware/sim I/O. It isn't wired into `SO101Arm.goal()`/`move()` yet, since no
shipped [`Command`](../../command/index.md) emits `(ActionType, {"dx", "dy"})`
commands (see `ROADMAP.md`); call it directly, as
`examples/08_mixed_classification_regression.ipynb` and
`examples/09_real_so101_arm_control.ipynb` do:

```python
from n2o.robot.arm.so101.lerobot_robot_so101_5dof.solver import SO101IKSolver

solver = SO101IKSolver()
target_deg, ik_error = solver.solve(current_deg, dx=0.02, dy=0.0)
```

## Simulation and provenance

Driving the arm in simulation is
[`Robot`'s job, not `SO101Arm`'s](../index.md#visualizing-with-simulator). The
bundled MJCF/Unity assets live alongside the driver code in `arm/so101/` (`mjcf/`,
`unity_model/`) — see that folder's `NOTICE.md` for CAD provenance
([`TheRobotStudio/SO-ARM100`](https://github.com/TheRobotStudio/SO-ARM100)).
