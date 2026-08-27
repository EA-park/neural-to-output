import threading
from enum import Enum

from . import arm, camera, hand, simulation, solver
from .part import Part


class ControllerType(Enum):
    """Which backend `Robot.router()` dispatches a part's command to -- see
    `docs/robot/index.ko.md` 기능 1."""

    SIMULATION = "simulation"
    MOTOR_DRIVER = "motor_driver"
    VLA = "vla"


class Robot:
    """Container binding an arm, hand, and camera together, and routing a translated
    command dict (`{"type", "arm", "hand"}`, from `Command.translate()`) to whichever
    of them the caller assigned.

    `self.controller` is a `ControllerType` -- `SIMULATION` means only `goal()` gets
    called (target values only), `MOTOR_DRIVER` means drive the real hardware via
    `move()`, `VLA` isn't implemented yet (see `ROADMAP.md`).
    `N2O.run(controller=...)` sets this before calling `router()`.

    `self.simulator` is `None` by default (`mujoco` is an `examples`/`demos`-group-only
    dependency, so `Robot` never imports it eagerly) -- assign a
    `n2o.robot.simulation.Simulator()` to actually visualize `SIMULATION`-mode
    `goal()` targets; `N2O.run(controller="simulation")` does this for you.
    """

    def __init__(self):
        self.arm: Part | None = None
        self.hand: Part | None = None
        self.camera: Part | None = None
        self.controller = ControllerType.SIMULATION
        self.simulator = None

    def router(self, actions: dict):
        """Dispatch every part named in `actions` on its own `threading.Thread` --
        `Robot` owns thread creation here (not `N2O`, not the `Part` itself). This is
        a real concurrency win despite the GIL: `Part.move()` (serial I/O +
        `time.sleep()` ramping) and `Simulator.drive()` (`mujoco.mj_step()`) both
        release the GIL while blocked, so e.g. the arm and hand actually move at the
        same time instead of one after another -- see `docs/robot/index.ko.md`.
        Threads are spawned fresh per call and joined before returning, so this
        method is still synchronous from the caller's point of view. If more than
        one part's thread raises, only the first (`arm` before `hand`) is re-raised
        here -- the others are silently dropped, a known limitation.

        Each part's `Part.done_event` is cleared right before its dispatch starts and
        set right after it finishes (success or failure) -- see `Part.done_event`."""
        results = {}
        errors = {}
        threads = []

        def _dispatch(part, cmd, obj):
            obj.done_event.clear()
            try:
                if self.controller is ControllerType.SIMULATION:
                    target = obj.goal(cmd)
                    results[part] = target
                    if self.simulator is not None:
                        self.simulator.drive(part, target)
                elif self.controller is ControllerType.MOTOR_DRIVER:
                    obj.move(cmd)
                    results[part] = "moved"
                elif self.controller is ControllerType.VLA:
                    raise NotImplementedError(
                        "ControllerType.VLA routing isn't implemented yet -- see ROADMAP.md"
                    )
            except BaseException as exc:  # noqa: BLE001 -- re-raised on the caller's thread below
                errors[part] = exc
            finally:
                # Signals this part reached its target (SIMULATION: after
                # Simulator.drive() finishes stepping; MOTOR_DRIVER: after move()
                # returns) -- also set on failure, so a waiter on done_event never
                # hangs on a part that errored.
                obj.done_event.set()

        for part in ("arm", "hand"):
            cmd = actions.get(part)
            obj = getattr(self, part)
            if cmd is None or obj is None:
                continue
            thread = threading.Thread(
                target=_dispatch, args=(part, cmd, obj), daemon=True
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        if errors:
            raise errors[next(part for part in ("arm", "hand") if part in errors)]

        return results


__all__ = [
    "ControllerType",
    "Part",
    "Robot",
    "arm",
    "camera",
    "hand",
    "simulation",
    "solver",
]
