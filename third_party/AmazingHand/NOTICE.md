# Provenance

`Demo/`, `PythonExample/`, `LICENSE`, and `README.md` are copied unmodified from the
[AmazingHand](https://github.com/pollen-robotics/AmazingHand) project (Pollen Robotics),
tag [`v1.0`](https://github.com/pollen-robotics/AmazingHand/tree/v1.0) (commit
[`23a262c`](https://github.com/pollen-robotics/AmazingHand/tree/23a262c94748ac061a63c6d32158a7f094c25b6e)).
Not a pip/uv-installable package — upstream ships no root `pyproject.toml`/`setup.py`,
just example scripts, a Rust/Python demo stack (`Demo/`), CAD, and docs. Vendored here
as reference material rather than pulled in as a dependency.

- Software (`PythonExample/`, `Demo/`, docs): Apache License 2.0.
- Mechanical design (CAD, meshes under `Demo/AHSimulation/`): [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/).

`src/n2o/robot/hand/amazing_hand_real/AmazingHandRealController` was ported from
`PythonExample/AmazingHand_Demo.py`'s `rustypot.Scs0009PyController` usage and its
per-motor calibration formula — kept here so that mapping stays checkable against the
original source instead of only the ported n2o code. `Demo/AHSimulation/` mjcf/CAD is
a separate, older vendored copy of the same hand model already lives at
`src/n2o/robot/hand/amazing_hand_right/` (commit `3e82410`, see that
directory's own `NOTICE.md`) — this copy is not re-used for the MuJoCo sim, it's kept
only because it's part of the vendored `Demo/` tree.

`Demo/HandTracking/` and `Demo/AHSimulation/` are standalone example apps with their own
`pyproject.toml`s (`mediapipe`/`opencv-python`/`dora-rs`, `mujoco`/`mink`/`dora-rs`
respectively) — not installed by this project's `uv` environment, reference only.
