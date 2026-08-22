from abc import ABC, abstractmethod
from typing import ClassVar

ARM_REGISTRY: dict[str, type["RobotArm"]] = {}


def register_arm(name: str):
    """Class decorator registering a `RobotArm` subclass under `name` for `RobotConfig`."""

    def decorator(cls: type["RobotArm"]) -> type["RobotArm"]:
        ARM_REGISTRY[name] = cls
        return cls

    return decorator


class RobotArm(ABC):
    """Base interface for a robot arm actuator."""

    input_spec: ClassVar[dict | None] = None
    """Shape/key contract for `move()`'s `command` argument. None means not yet decided.
    Checked against the command (or decoder) `output_spec` by `CommandConfig.verify_report()`."""

    @abstractmethod
    def move(self, decoder_type, command):
        """Actuate the arm according to a decoded command.

        `decoder_type` is `decoder.config.type` (a `DecoderType` or tuple of them) — passed
        through from `Command.translate()` in case `move()`/its `Controller` needs to branch
        on it; `command` is this part's own value (a bare name or an `(ActionType, value)`
        tuple — see `n2o.command.Command`)."""
        raise NotImplementedError
