from abc import ABC, abstractmethod
from typing import ClassVar

CAMERA_REGISTRY: dict[str, type["RobotCamera"]] = {}


def register_camera(name: str):
    """Class decorator registering a `RobotCamera` subclass under `name` for `RobotConfig`."""

    def decorator(cls: type["RobotCamera"]) -> type["RobotCamera"]:
        CAMERA_REGISTRY[name] = cls
        return cls

    return decorator


class RobotCamera(ABC):
    """Base interface for a robot-mounted camera."""

    output_spec: ClassVar[dict | None] = None
    """Shape/dtype contract for what `capture()` returns. None means not yet decided."""

    @abstractmethod
    def capture(self):
        """Return the latest captured frame."""
        raise NotImplementedError
