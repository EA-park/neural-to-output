# Adding a Component

To add a new dataset, decoder, or robot:

1. Create a new file next to the existing ones in the relevant package (e.g.
   `src/n2o/decoder/my_decoder.py`).
2. Subclass that package's `base.py` ABC and implement its abstract method(s).
3. Re-export the new class from that package's `__init__.py`.

New robot parts (e.g. a leg or head for a future humanoid) follow the same pattern as
a new sibling package under `n2o.robot`. An integrated device that drives both an arm
and a hand from one physical connection doesn't need a structural change — implement
a single class that inherits from both `RobotArm` and `RobotHand`, and assign the same
instance to both `robot.arm` and `robot.hand`.
