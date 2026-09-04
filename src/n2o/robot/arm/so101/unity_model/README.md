# SO-101 arm -- Unity local package

Unity-side counterpart to [`../mjcf/`](../mjcf) (the MuJoCo model of the same arm) --
this package owns the SO-101's 3D model for the Unity simulation backend, the same way
`../mjcf/` owns it for the MuJoCo backend. Meant to be pulled into a Unity project (this
repo doesn't ship one -- see `src/n2o/robot/simulation/unity/unity_simulator.py`'s own
docstring for the Python-side TCP client and wire protocol) as a local package
(`"file:.../arm/so101/unity_model"` in that project's `Packages/manifest.json`), not
copied in directly -- one model, imported from wherever it's actually owned.

## Status

Scaffold only -- `Models/`/`Prefabs/` are empty. Still needed:

- Import the SO-101 meshes into Unity (either re-export `../mjcf/mjcf/assets/*.stl` to a
  Unity-friendly format, or re-import from the original
  [SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) CAD source -- see
  `../NOTICE.md` for that model's provenance/license, which any Unity-side re-export of
  the same geometry inherits).
- Build a prefab (`Prefabs/SO101Arm.prefab`) with a joint hierarchy matching
  `../mjcf/mjcf/scene.xml`'s joint names (`shoulder_pan`, `shoulder_lift`, `elbow_flex`,
  `wrist_flex`, `wrist_roll`, `gripper`) so a Unity-side socket listener can drive them
  by name from `UnitySimulator`'s `{"part": "arm", "target": {joint: degrees}}`
  messages (see `src/n2o/robot/simulation/unity/unity_simulator.py`'s own docstring for
  the exact wire format).

This needs the real Unity Editor to do -- not something generated from this repo.

## Relationship to the two automated engines

This hand-authored prefab workflow predates, and is now a third, fully-manual
alternative to, two automated ways of getting this arm into Unity -- see the
companion `neural-to-output-unity` repo's own README: the official MuJoCo Unity
plugin (loads `../mjcf/so101_new_calib.xml` directly, no conversion at all) or
`RigLoader.cs` (builds an `ArticulationBody` rig at Play time from a JSON
descriptor `n2o.robot.simulation.unity.solver.ClosedLoopRigSolver` generates from
that same MJCF). Both avoid the manual mesh re-export and prefab-building steps
above entirely. This folder's own scaffold is only worth finishing by hand if you
specifically want a real Unity `.prefab` asset (e.g. to hand-edit further in the
Editor) rather than something built at runtime.
