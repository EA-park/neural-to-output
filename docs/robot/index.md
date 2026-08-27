# Robot

[`Robot`][n2o.robot.Robot] is the hub binding a robot's parts (`arm`/`hand`/`camera`) together. It takes
the command dict [`Command.translate()`](../command/index.md) built and:

1. decides which part(s) it targets,
2. and — via `ControllerType` — decides *how* to drive that part (real hardware,
   simulation, or a vision-language-action model).

## The `Part` interface

Every part `Robot` can route to (e.g. `AmazingHand`) implements [`n2o.robot.Part`][n2o.robot.part.Part]:

```python
class Part(ABC):
    def goal(self, cmd):
        """Compute a target only -- no I/O, nothing physically moves."""

    def move(self, cmd):
        """Drive the real hardware toward `cmd`."""
```

- `goal(cmd)` — pure computation, useful for previewing a target without touching
  hardware; no I/O, nothing physically moves.
- `move(cmd)` — actually drives the real hardware.
- `done_event` (a `threading.Event`, already implemented on `Part` itself --
  subclasses don't need to add it) -- `Robot.router()` clears it right before
  dispatching this part, and sets it once the part finishes moving toward its target
  (`SIMULATION`: after `Simulator.drive()`; `MOTOR_DRIVER`: after `move()` -- either
  way, even on failure). Other code can `part.done_event.wait()`/`.is_set()` to wait
  on or check that part's completion -- see "Dispatching parts concurrently" below
  and the "Sequencing with `py_trees`" item in `ROADMAP.md`.

`move(cmd)` must not just *send* the command and return right away -- for
`done_event` to actually mean "finished moving," `move()` itself has to block for
the real (or a realistic estimated) travel time. `SO101Arm` does this with a
real-time ramp; `AmazingHand` with an estimated `MOVE_SETTLE_S` sleep.

A part implementation owns its own hardware connection (e.g. `AmazingHand` lazily
owns a `rustypot` serial connection) — `Robot` itself never talks to hardware
directly.

## `ControllerType` and routing

`Robot.controller` holds a [`ControllerType`][n2o.robot.ControllerType] value (`SIMULATION`/`MOTOR_DRIVER`/`VLA`).
`Robot.router(actions)` reads it once per call to decide, for every part named in
`actions`, whether to call `goal()` or `move()`:

| `ControllerType` | What `router()` calls                  | Status                                          |
| ----------------- | ---------------------------------------- | -------------------------------------------------- |
| `SIMULATION`       | `part.goal(cmd)` — target only, visualized too if `robot.simulator` is set | Implemented |
| `MOTOR_DRIVER`      | `part.move(cmd)` — drives real hardware    | Implemented                                        |
| `VLA`                 | *(planned)* `part.<command>()` with camera input | Not implemented — raises `NotImplementedError`       |

```python
from n2o.robot import ControllerType, Robot
from n2o.robot.arm.so101 import SO101Arm

robot = Robot()
robot.arm = SO101Arm(port="/dev/ttyACM0")
robot.controller = ControllerType.MOTOR_DRIVER
robot.router({"arm": "up", "hand": None})
```

`N2O.run(controller=...)` sets `robot.controller` for you before calling `router()`:

- `"motor_driver"`
- `"simulation"` — also builds a `Simulator()` onto `robot.simulator` if none is
  assigned yet, and opens a viewer for every part that's actually assigned. See the
  `Simulator` section below.
- `"vla"`

## Dispatching parts concurrently

`router()` drives every part in `actions` **on its own thread** -- creating,
starting, and joining those threads is entirely `Robot`'s job (not `N2O`'s, not the
`Part`'s). It spawns one thread per part on every call and joins all of them before
returning, so it's still a synchronous call from the outside.

Python threads are well known for not giving real parallelism on CPU-bound work
(the GIL), but `Part.move()` (serial I/O + `time.sleep()` ramping) and
`Simulator.drive()` (`mujoco.mj_step()`) are both I/O-bound -- they release the GIL
while blocked -- so threading them is a genuine win here: the arm and hand actually
move **at the same time** instead of one after the other.

```python
import time
robot.arm.move("up")     # sequentially: ~0.5s + ~0.5s
robot.hand.move("grip")  # (calling directly like this is illustrative -- router() threads it)
```
Calling `router({"arm": "up", "hand": "grip"})` instead takes as long as the slower
of the two, not their sum.

!!! note "Limitation"
    If both the arm and hand fail in the same call, `router()` only re-raises one of
    them (`arm` takes priority) -- the other error is silently dropped. Accepted as a
    simplification since simultaneous dual failures aren't a common case today.

`router()`'s own return already means "every part is done" (it only returns after
joining), but to wait on or check just one part -- from another thread, say -- use
`part.done_event` directly:

```python
robot.arm.done_event.wait()  # blocks until the arm finishes moving to this target
```

## Visualizing with `Simulator`

When `robot.simulator` isn't `None`, `SIMULATION`-mode `router()` hands each
computed `goal()` value to `Simulator.drive(part, target)` (`n2o.robot.simulation.Simulator`),
which actually drives a MuJoCo model:

> `mujoco` is an `examples`/`demos`-group-only dependency, so `Robot` never imports
> it for you -- assign one explicitly.

```python
from n2o.robot import ControllerType, Robot
from n2o.robot.hand.amazing_hand import AmazingHand
from n2o.robot.simulation import Simulator

robot = Robot()
robot.hand = AmazingHand()
robot.controller = ControllerType.SIMULATION
robot.simulator = Simulator()
robot.simulator.launch_viewer("hand")  # omit to stay headless -- physics only, no window
robot.router({"hand": "grip", "arm": None})
```

`Simulator.drive()` itself never touches a GL context, so it's safe in headless
environments (CI); a viewer window only opens if `launch_viewer(part)` is called
explicitly. `N2O.run(controller="simulation")` does both steps (building the
`Simulator` and calling `launch_viewer()`) for you.

!!! note "Not the other `controller`"
    `Robot.controller` (`ControllerType`) picks a *backend* for an already-resolved
    per-part command. It's a different concept from `n2o.controller`
    (`LanguageController`), which handles an entire `FeatureType.LANGUAGE`
    prediction — see [Controller](../controller/index.md) for that distinction.

!!! warning "Arm/Hand/Camera pages are still on the previous design"
    The [Arm](arm/index.md), [Hand](hand/index.md), and [Camera](camera/index.md)
    pages still describe the previous `RobotArm`/`RobotHand`/`RobotCamera` +
    registry design (`@register_arm`, `RobotConfig`, `Controller.apply()`). They
    haven't been updated yet for the `Part`/`ControllerType`/`Robot.router()` design
    described here.

## Roadmap

Not yet implemented — see
[ROADMAP.md](https://github.com/EA-park/neural-to-output/blob/main/ROADMAP.md) for
details:

- **Per-part configuration** (optionally from `.yml`): controller settings, solver
  settings, motor IDs, DOF, simulation model path, a stable port ID, calibration
  file/matrix
- **Multiple parts of the same kind** (e.g. `left_arm`/`right_arm`), including a hand
  driven directly by its own arm rather than as a separate part
- **Cross-part execution coordination** — the basic signal (`Part.done_event`) is
  implemented. What's left is actually using it to sequence dependent or cooperative
  multi-part tasks — a [`py_trees`](https://py-trees.readthedocs.io/) adoption is
  under consideration, see "Sequencing with `py_trees`" in `ROADMAP.md`
- **`VLA` routing** — calling each part's own command method with camera input
  attached
