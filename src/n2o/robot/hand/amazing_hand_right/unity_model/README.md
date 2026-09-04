# AmazingHand (right) -- Unity local package

Unity-side counterpart to [`../mjcf/`](../mjcf) (the MuJoCo model of the same hand) --
this package owns AmazingHand's 3D model for the Unity simulation backend, the same way
`../mjcf/` owns it for the MuJoCo backend. Meant to be pulled into a Unity project (this
repo doesn't ship one -- see `src/n2o/robot/simulation/unity/unity_simulator.py`'s own
docstring for the Python-side TCP client and wire protocol) as a local package
(`"file:.../hand/amazing_hand_right/unity_model"` in that project's
`Packages/manifest.json`), not copied in directly -- one model, imported from wherever
it's actually owned.

## Status

Scaffold only -- `Models/`/`Prefabs/` are empty. Still needed:

- Import AmazingHand's meshes into Unity (either re-export `../mjcf/mjcf/assets/*.stl`
  to a Unity-friendly format, or re-import from the original
  [AmazingHand](https://github.com/pollen-robotics/AmazingHand) CAD source -- see
  `../NOTICE.md` for that model's provenance/license, which any Unity-side re-export of
  the same geometry inherits).
- Build a prefab (`Prefabs/AmazingHand.prefab`) with a joint hierarchy matching
  `../mjcf/mjcf/robot.xml`'s actuator names (`finger1_motor1`, `finger1_motor2`,
  `finger2_motor1`, ... `finger4_motor2`, 8 total) so a Unity-side socket listener can
  drive them by position index from `UnitySimulator`'s
  `{"part": "hand", "target": [8 floats]}` messages (see
  `src/n2o/robot/simulation/unity/unity_simulator.py`'s own docstring for the exact
  wire format).

This needs the real Unity Editor to do -- not something generated from this repo.

## Relationship to the two automated engines

This hand-authored prefab workflow predates, and is now a third, fully-manual
alternative to, two automated ways of getting this hand into Unity -- see the
companion `neural-to-output-unity` repo's own README: the official MuJoCo Unity
plugin (loads `../mjcf/robot.xml` directly, full physics fidelity including the
real ball-joint/`<equality><connect>` closed-loop mechanism, since it's genuinely
MuJoCo's own solver) or `RigLoader.cs` (builds an `ArticulationBody` rig at Play
time from a JSON descriptor `n2o.robot.simulation.unity.solver
.ClosedLoopRigSolver` generates from that same MJCF, bridging the closed loop
with a `ConfigurableJoint` -- see `DECISIONS.md`'s 2026-09-04 entry for why a
hand-built prefab following the naive joint hierarchy above would actually miss
this mechanism's real coupled motion, unlike either automated engine). This
folder's own scaffold is only worth finishing by hand if you specifically want a
real Unity `.prefab` asset rather than something built at runtime.
