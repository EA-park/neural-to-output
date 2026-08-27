import threading
from abc import ABC, abstractmethod


class Part(ABC):
    """Base interface for a robot part (hand/arm/...) that `Robot.router()` dispatches
    to. `goal()` computes a target with no I/O -- used when `Robot.controller` means
    simulation, so nothing physically moves. `move()` actually drives the real
    hardware."""

    @abstractmethod
    def goal(self, cmd):
        raise NotImplementedError

    @abstractmethod
    def move(self, cmd):
        raise NotImplementedError

    @property
    def done_event(self):
        """`threading.Event` `Robot.router()` clears right before dispatching this
        part and sets right after it finishes moving toward a target -- in both the
        `SIMULATION` (after `Simulator.drive()`) and `MOTOR_DRIVER` (after `move()`)
        cases, and even if that raised, so a caller waiting on it never hangs on a
        failed part. Lets other code (e.g. a future cross-part coordinator, see
        `ROADMAP.md`) block on/poll one part's completion via `part.done_event.wait()`/
        `.is_set()` instead of only trusting `router()`'s own return.

        Created lazily on first access (not `__init__`) so existing `Part`
        subclasses that don't call `super().__init__()` still get one."""
        if not hasattr(self, "_done_event"):
            self._done_event = threading.Event()
        return self._done_event
