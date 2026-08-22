from abc import ABC, abstractmethod
from typing import ClassVar

CONTROLLER_REGISTRY: dict[str, type["LanguageController"]] = {}


def register_controller(name: str):
    """Class decorator registering a `LanguageController` subclass under `name` for `RobotConfig`."""

    def decorator(cls: type["LanguageController"]) -> type["LanguageController"]:
        CONTROLLER_REGISTRY[name] = cls
        return cls

    return decorator


def make_controller(name: str) -> "LanguageController":
    """Build a `LanguageController` by its registered name (see `RobotConfig.controller`)."""
    return CONTROLLER_REGISTRY[name]()


class LanguageController(ABC):
    """Base interface for routing a `FeatureType.LANGUAGE` command to a robot.

    Sits between a decoder's language-typed command and `robot.arm/hand.move()` — the
    `FeatureType.ACTION` path keeps going straight to `robot.arm/hand.move()` (or
    through `Command`/`n2o.robot.controller.Controller` — see `docs/architecture.md`).
    Takes `robot` as an argument (rather than storing a reference) so it stays as
    stateless as every other pipeline stage.

    Not to be confused with `n2o.robot.controller.Controller` (renamed from
    `MotorWrapper`), which is a per-robot-part dispatcher for a single named action —
    an unrelated, lower-level concept that happens to share the word "controller".
    """

    input_spec: ClassVar[dict | None] = None
    output_spec: ClassVar[dict | None] = None

    @abstractmethod
    def act(self, command, robot):
        """Drive `robot` according to a `FeatureType.LANGUAGE` command."""
        raise NotImplementedError
