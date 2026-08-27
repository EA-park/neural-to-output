from . import arm, camera, hand, language_controller
from .config import RobotConfig, make_robot
from .controller import Controller


class Robot:
    """Container that binds a robot arm, hand, and camera together."""

    def __init__(self):
        self.arm = None
        self.hand = None
        self.camera = None

    @classmethod
    def from_config(cls, config: RobotConfig) -> "Robot":
        """Build a `Robot` from a `RobotConfig` — see `make_robot()`."""
        return make_robot(config)


__all__ = [
    "Controller",
    "Robot",
    "RobotConfig",
    "arm",
    "camera",
    "hand",
    "language_controller",
    "make_robot",
]
