from .base import RobotHand, register_hand


@register_hand("AmazingHand")
class AmazingHand(RobotHand):
    """Driver for the AmazingHand robot hand."""

    def move(self, decoder_type, command):
        raise NotImplementedError
