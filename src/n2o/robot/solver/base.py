from abc import ABC, abstractmethod


class Solver(ABC):
    """Base interface for a robot-part solver -- pure computation, no I/O (no
    hardware/sim access). Turns a high-level target (e.g. a Cartesian offset) into
    the raw values a part's own `goal()`/`move()` can act on.

    Kept separate from `Solver`'s namesake ambiguity risk with `Robot.controller`
    (the real/simulation dispatch flag) and the removed `Controller` ABC: a solver
    never drives hardware or a simulator itself, it only computes a target for
    something else to execute.
    """

    @abstractmethod
    def solve(self, *args, **kwargs):
        """Compute and return a target -- no side effects."""
        raise NotImplementedError
