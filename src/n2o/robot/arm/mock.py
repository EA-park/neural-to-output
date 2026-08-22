from .base import RobotArm, register_arm


@register_arm("MockArm")
class MockArm(RobotArm):
    """No-op arm for testing without real hardware."""

    def move(self, decoder_type, command):
        print(f"MockArm.move({decoder_type!r}, {command!r})")
