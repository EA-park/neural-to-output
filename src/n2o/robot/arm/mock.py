from .base import RobotArm


class MockArm(RobotArm):
    """No-op arm for testing without real hardware."""

    def move(self, command):
        print(f"MockArm.move({command!r})")
