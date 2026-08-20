from .base import RobotArm


class LeRobotSO101(RobotArm):
    """Driver for the LeRobot SO-101 arm."""

    def move(self, command):
        raise NotImplementedError
