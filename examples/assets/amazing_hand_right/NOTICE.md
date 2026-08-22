# Provenance

The MuJoCo model in `mjcf/` (`robot.xml`, `scene.xml`, `keyframes.xml`,
`joints_properties.xml`, `additional.xml`, `config.json`, `assets/*.stl`) is copied
unmodified from the [AmazingHand](https://github.com/pollen-robotics/AmazingHand)
project (Pollen Robotics), `Demo/AHSimulation/AHSimulation/AH_Right/mjcf/` at commit
[`3e82410`](https://github.com/pollen-robotics/AmazingHand/tree/3e8241074df3436a3044ced4881e3bb2133aa725/Demo/AHSimulation/AHSimulation/AH_Right/mjcf),
generated from their CAD via [onshape-to-robot](https://github.com/Rhoban/onshape-to-robot).
`demo_scene.xml` is the one file in this directory that is **not** an upstream copy —
see its own header comment.

- Software (this simulation node/build tooling): Apache License 2.0.
- Mechanical design (CAD, meshes): [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/).

Used here to visually drive the `AmazingHand` robot hand from
`02_hand_intent_classification_amazinghand.ipynb` via plain MuJoCo joint position control
(no IK, no `mink`/`dora-rs` — those are only needed for the original project's fingertip
IK demo).
