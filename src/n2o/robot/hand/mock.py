from .base import RobotHand


class MockHand(RobotHand):
    """No-op hand for testing without real hardware."""

    def move(self, command):
        print(f"MockHand.move({command!r})")
