from .base import RobotArm, register_arm


@register_arm("Gello")
class Gello(RobotArm):
    """Driver for a Gello-teleoperated arm."""

    def move(self, decoder_type, command):
        raise NotImplementedError
