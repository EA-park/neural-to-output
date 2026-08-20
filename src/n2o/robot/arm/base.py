from abc import ABC, abstractmethod


class RobotArm(ABC):
    """Base interface for a robot arm actuator."""

    @abstractmethod
    def move(self, command):
        """Actuate the arm according to a decoded command."""
        raise NotImplementedError
