# n2o.robot.arm

Mirrors [`src/n2o/robot/arm/`](https://github.com/EA-park/neural-to-output/tree/main/src/n2o/robot/arm).

`lerobot_robot_so101_5dof/` is a verbatim vendored copy of a private local package (a
`lerobot`-framework `Robot`/`RobotConfig`, not an `n2o.robot.Part`) and isn't
documented here — see `CLAUDE.md`. `SO101IKSolver`, also inside that folder, is an
exception: it's `n2o`-authored (not vendored), placed there because it's specific to
this 5-DOF driver rather than a general SO-101-arm-shaped thing — see `ROADMAP.md`.

::: n2o.robot.arm.so101.SO101Arm

::: n2o.robot.arm.so101.lerobot_robot_so101_5dof.solver.SO101IKSolver
