# Controller

Documentation for routing a language-typed decoded prediction to a robot.

## The `controller.act()` contract

For a decoder whose `output_type` is `FeatureType.LANGUAGE`, `N2O.run()` skips
[`Command`](../command/index.md) entirely and calls `self.controller.act(decoded_signal,
self.robot)` instead — the answer for VLA-style (vision-language-action) instructions,
where there's no fixed per-part action shape to translate into:

```python
class LanguageController(ABC):
    def act(self, command, robot):
        """Drive `robot` according to a FeatureType.LANGUAGE decoded prediction."""
```

It takes `robot` as an argument rather than storing a reference, keeping it as
stateless as every other pipeline stage. See
[Architecture → Routing](../architecture.md#routing-featuretype-and-controller).

!!! note
    No concrete `LanguageController` implementation ships in this snapshot of the
    repo — `n2o.controller` is currently being reworked. Set `n2o.controller` to any
    object exposing `act(decoded_signal, robot)` to use a `FeatureType.LANGUAGE`
    decoder in the meantime.

## Not the same thing as `n2o.robot.controller.Controller`

The two classes share the word "controller" but solve different problems at different
points in the pipeline:

|                     | `controller.act()`                                  | `n2o.robot.controller.Controller`                          |
| ------------------- | ----------------------------------------------------- | -------------------------------------------------------------- |
| Lives on            | `N2O` (`n2o.controller`)                               | A `RobotArm`/`RobotHand` implementation                        |
| Handles             | An entire `FeatureType.LANGUAGE` decoded prediction    | One already-resolved per-part action                           |
| Called by           | `N2O.run()`, in place of `Command`                     | `robot.arm.move()`/`robot.hand.move()`                          |
| Produces             | Whatever robot behavior the instruction implies         | A vendor SDK call or raw motor targets (see [Arm](../robot/arm/index.md#move-and-controller)) |

## Registry and `RobotConfig`

Like `robot.arm`/`robot.hand`/`robot.camera`, a controller is expected to register
itself via `@register_controller("Name")`, with `RobotConfig(controller="...")` naming
which one a pipeline intends to use — resolved with `make_controller(...)`, then
assigned to `n2o.controller` directly (`RobotConfig`'s `controller` field isn't
resolved by `make_robot()`/`Robot.from_config()`, since a language controller lives on
`N2O`, not `Robot`).
