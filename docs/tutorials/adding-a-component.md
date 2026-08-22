# Adding a Component

To add a new dataset, decoder, or robot:

1. Create a new file next to the existing ones in the relevant package (e.g.
   `src/n2o/decoder/my_decoder.py`).
2. Subclass that package's `base.py` ABC and implement its abstract method(s).
3. Re-export the new class from that package's `__init__.py`.

New robot parts (e.g. a leg or head for a future humanoid) follow the same pattern as
a new sibling package under `n2o.robot`, alongside `arm`/`hand`/`camera`. An
integrated device that drives both an arm and a hand from one physical connection
doesn't need a structural change — implement a single class that inherits from both
`RobotArm` and `RobotHand`, and assign the same instance to both `robot.arm` and
`robot.hand`. `n2o.controller` follows the identical `base.py`+concrete+`__init__.py`
shape too.

If the new class is a named, reusable piece of hardware (rather than an ad hoc or
simulated stand-in), you can optionally decorate it with `@register_arm("Name")`
(or `@register_hand`/`@register_camera`/`@register_controller`, matching the
package) to make it selectable via `RobotConfig` — see
[Architecture → Building a robot from a `RobotConfig`](../architecture.md#building-a-robot-from-a-robotconfig).
This step is optional: direct instantiation and attribute assignment always work
without it.
