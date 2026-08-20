from .base import RobotHand


class AmazingHand(RobotHand):
    """Driver for the AmazingHand robot hand."""

    def move(self, command):
        raise NotImplementedError
