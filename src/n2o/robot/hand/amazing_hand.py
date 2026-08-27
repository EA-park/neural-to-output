from ..controller import Controller
from .base import RobotHand, register_hand


@register_hand("AmazingHand")
class AmazingHand(RobotHand):
    """Driver for the AmazingHand robot hand."""

    def __init__(self, controller: Controller | None = None):
        self.controller = controller

    def move(self, decoder_type, command):
        if self.controller is None:
            raise RuntimeError(
                f"{type(self).__name__}.controller is not set — assign a Controller "
                "instance before calling move() (see CLAUDE.md's Architecture section)"
            )
        return self.controller.apply(decoder_type, command)
