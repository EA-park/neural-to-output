from ..controller import Controller
from .base import RobotArm, register_arm


@register_arm("LeRobotSO101")
class LeRobotSO101(RobotArm):
    """Driver for the LeRobot SO-101 arm."""

    def __init__(self, controller: Controller | None = None):
        self.controller = controller

    def move(self, decoder_type, command):
        if self.controller is None:
            raise RuntimeError(
                f"{type(self).__name__}.controller is not set — assign a Controller "
                "instance before calling move() (see CLAUDE.md's Architecture section)"
            )
        return self.controller.apply(decoder_type, command)
