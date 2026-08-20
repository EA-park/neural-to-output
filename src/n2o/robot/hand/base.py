from abc import ABC, abstractmethod


class RobotHand(ABC):
    """Base interface for a robot hand actuator."""

    @abstractmethod
    def move(self, command):
        """Actuate the hand according to a decoded command."""
        raise NotImplementedError
