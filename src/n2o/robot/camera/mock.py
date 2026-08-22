from .base import RobotCamera, register_camera


@register_camera("MockCamera")
class MockCamera(RobotCamera):
    """No-op camera for testing without real hardware."""

    def capture(self):
        print("MockCamera.capture()")
