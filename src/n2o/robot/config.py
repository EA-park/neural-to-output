from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .arm.base import ARM_REGISTRY
from .camera.base import CAMERA_REGISTRY
from .hand.base import HAND_REGISTRY

if TYPE_CHECKING:
    from . import Robot


@dataclass(slots=True)
class RobotConfig:
    """Names a `Robot`'s parts by registry key, for `make_robot()`/`Robot.from_config()`.

    Additive to direct attribute assignment (`robot.arm = SomeInstance()`) — ad hoc or
    simulated components (e.g. a notebook's one-off `RobotHand` subclass) are never
    registered and must still be assigned directly; this only covers named, reusable
    hardware. `controller` names a `Controller` (see `n2o.controller`) — it lives on
    `N2O`, not `Robot`, so `make_robot()` doesn't resolve it; use
    `n2o.controller.make_controller()` for that field.
    """

    arm: str | None = None
    hand: str | None = None
    camera: str | None = None
    controller: str | None = None


def make_robot(config: RobotConfig) -> Robot:
    """Build a `Robot` from a `RobotConfig`, resolving its `arm`/`hand`/`camera` fields
    via their registries. `config.controller` is not resolved here — see the class
    docstring."""
    from . import Robot

    robot = Robot()
    if config.arm is not None:
        robot.arm = ARM_REGISTRY[config.arm]()
    if config.hand is not None:
        robot.hand = HAND_REGISTRY[config.hand]()
    if config.camera is not None:
        robot.camera = CAMERA_REGISTRY[config.camera]()
    return robot
