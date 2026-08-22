from abc import ABC, abstractmethod


class Controller(ABC):
    """Base interface for translating a per-part action name into vendor/hardware calls.

    Owned by a `RobotArm`/`RobotHand` implementation; `move()` delegates to this so the
    semantic command boundary (the one `N2O.verify()` checks) stays separate from
    vendor-specific motor control. Two shapes are expected depending on what the vendor
    API offers: calling its existing discrete commands directly (e.g. `grip()`/`release()`),
    or hardcoding the action-to-motor-target mapping when the vendor API only takes raw
    motor targets.
    """

    @abstractmethod
    def apply(self, decoder_type, command):
        """Drive the underlying hardware/vendor API according to an action/command.

        Mirrors `RobotArm.move()`/`RobotHand.move()`'s signature, which typically delegates
        straight here."""
        raise NotImplementedError
