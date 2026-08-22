from .base import RobotArm, register_arm


@register_arm("LeRobotSO101")
class LeRobotSO101(RobotArm):
    """Driver for the LeRobot SO-101 arm."""

    def move(self, decoder_type, command):
        raise NotImplementedError
