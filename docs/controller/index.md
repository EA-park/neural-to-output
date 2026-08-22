# Controller

Documentation for routing a language-typed decoded command to a robot.

## `LanguageController`

`LanguageController` (in `n2o.controller`) sits between a `FeatureType.LANGUAGE`-typed decoder command and `robot.arm/hand.move()` — the previously-vague "middleware" stage's answer for VLA-style (vision-language-action) instructions. `FeatureType.ACTION` commands keep going straight through `Command` to `robot.arm/hand.move()` — see [Architecture → `Command`](../architecture.md#command-turning-a-decoders-raw-output-into-per-part-actions) — unaffected.

```python
from n2o.controller import LanguageController


class LanguageController(ABC):
    def act(self, command, robot):
        """Drive `robot` according to a `FeatureType.LANGUAGE` command."""
```

It takes `robot` as an argument rather than storing a reference, keeping it as stateless as every other pipeline stage. `N2O.run()` calls it automatically when `n2o.decoder.output_type is FeatureType.LANGUAGE` — see [Architecture → Routing](../architecture.md#routing-featuretype-and-languagecontroller).

**Not the same thing as `n2o.robot.controller.Controller`** (renamed from `MotorWrapper`) — that's an unrelated, lower-level concept: a per-robot-part dispatcher that turns a single action (e.g. `"grip"`, or an `(ActionType, value)` tuple) into a vendor SDK call or raw motor targets via `apply(decoder_type, action)`, owned by a `RobotArm`/`RobotHand` implementation. The two classes share the word "controller" but solve different problems at different points in the pipeline.

## Registry and `RobotConfig`

Like `robot.arm`/`robot.hand`/`robot.camera`, a `LanguageController` registers itself via `@register_controller("Name")`, and `RobotConfig(controller="VLA")` names which one a pipeline intends to use (resolved with `n2o.controller.make_controller("VLA")`, then assigned to `n2o.controller` — `RobotConfig`'s `controller` field isn't resolved by `make_robot()`/`Robot.from_config()`, since `LanguageController` lives on `N2O`, not `Robot`).

Only `VLAController` exists today, and it's an interface-only stub (`raise NotImplementedError`).
