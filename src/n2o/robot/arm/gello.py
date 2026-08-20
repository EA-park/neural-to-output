from .base import RobotArm


class Gello(RobotArm):
    """Driver for a Gello-teleoperated arm."""

    def move(self, command):
        raise NotImplementedError
