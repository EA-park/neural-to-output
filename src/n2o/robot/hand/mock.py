from .base import RobotHand, register_hand


@register_hand("MockHand")
class MockHand(RobotHand):
    """No-op hand for testing without real hardware."""

    def move(self, decoder_type, command):
        print(f"MockHand.move({decoder_type!r}, {command!r})")
