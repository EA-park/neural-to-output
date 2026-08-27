# Adding a Component

## A new dataset, stream, robot part, or decoder

Most of `src/n2o/` follows the same extension pattern:

1. Create a new file next to the existing ones in the relevant package (e.g.
   `src/n2o/robot/camera/my_camera.py`).
2. Subclass that package's `base.py` ABC (`decoder/base.py`, `robot/camera/base.py`,
   ...) and implement its abstract method(s) — for a decoder, subclass
   [`Classification` or `Regression`](../decoder/index.md#classification-vs-regression),
   not `Decoder` directly, unless its `preprocess()`/`window()` genuinely needs a third
   shape neither one provides.
3. Re-export the new class from that package's `__init__.py`.
4. If it's a named, reusable piece of hardware (rather than an ad hoc or simulated
   stand-in), decorate it with `@register_arm("Name")` (or `@register_hand`/
   `@register_camera`/`@register_controller`, matching the package) to make it
   selectable via `RobotConfig` — see
   [Architecture → Building a robot from a `RobotConfig`](../architecture.md#building-a-robot-from-a-robotconfig).
   This step is optional: direct instantiation and attribute assignment always work
   without it.

New robot parts (e.g. a leg or head for a future humanoid) follow the same pattern as a
new sibling package under `n2o.robot`, alongside `arm`/`hand`/`camera`. An integrated
device that drives both an arm and a hand from one physical connection doesn't need a
structural change — implement a single class that inherits from both `RobotArm` and
`RobotHand`, and assign the same instance to both `robot.arm` and `robot.hand`.

`signal/dataset/` is a partial exception: a new **moabb** dataset needs no code (it's
already registered under its class name in `moabb.datasets.utils.dataset_list` — check
`DatasetLoader.list_libraries()`). A dataset moabb doesn't cover needs a hand-written
`DatasetLibraryEntry` subclass with `@register_dataset("Name")` instead — or, for a
local recording rather than a redistributable dataset, skip the registry entirely and
use `n2o.signal.dataset.write_metadata_template(path)` + `DatasetLoader(path=...)`.

## A new `Command`

Unlike the above, `Command` isn't a `base.py`+concrete-implementation pattern — it's a
plain overridable class, usually subclassed notebook-local since it encodes one
specific decoder's raw output → one specific robot's parts. Only promote a `Command`
subclass into `src/n2o/command/` if it's genuinely reusable across notebooks (like
`GripSpreadCommand`/`OfnerCommand` — see [Command](../command/index.md)).

## A vendored (non-pip) dependency

If the hardware you're adding a driver for ships reference code that isn't a
pip/uv-installable package, see [Third-Party](../third-party/index.md) for how to
vendor it into `third_party/` instead of trying to add it as a normal dependency.
