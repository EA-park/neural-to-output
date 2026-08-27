# Provenance

The URDF/MuJoCo model in `mjcf/` (`so101_new_calib.xml`, `so101_new_calib.urdf`,
`scene.xml`, `joints_properties.xml`, `assets/*.stl`) is copied unmodified from the
[SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) project (The Robot Studio),
`Simulation/SO101/`, at commit
[`7629d2a`](https://github.com/TheRobotStudio/SO-ARM100/tree/7629d2ad9853d10fb903093a33ef6114099d97e5/Simulation/SO101),
generated from their CAD via [onshape-to-robot](https://github.com/Rhoban/onshape-to-robot).
This is the hardware/CAD repo behind `huggingface/lerobot`'s `SO101Follower` driver —
`lerobot` itself ships no simulation model, only a real serial-port hardware driver.

License: Apache License 2.0 (whole `SO-ARM100` repo, code and CAD alike — no separate
CAD license file).

Uses the "new calibration" variant (`so101_new_calib.xml`, joint zero = middle of each
joint's range) rather than "old calibration" (zero = fully extended horizontally); see
that repo's `Simulation/SO101/README.md` for details. Note: per that README, `lerobot`
represents the gripper as a linear 0 (closed)–100 (open) joint, which this MJCF's
`gripper` joint (radians) does not natively encode — callers must convert.

Joint names match `lerobot`'s `SO101Follower` exactly: `shoulder_pan`, `shoulder_lift`,
`elbow_flex`, `wrist_flex`, `wrist_roll`, `gripper`.
