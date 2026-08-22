from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..decoder.config import FeatureType

if TYPE_CHECKING:
    from .verify import VerificationReport


@dataclass(slots=True)
class CommandConfig:
    """Design-time contract for the command flowing between `decoder` and `robot`.

    Replaces the old `MiddlewareSpec` placeholder, joining the `SignalConfig`/
    `DecoderConfig`/`RobotConfig` family. `input_feature`/`output_feature` are compared
    as plain dicts against the neighboring stages' specs by `verify_report()`; their
    exact shape isn't finalized yet. `output_type` is declarative only — it's not read
    by `N2O.run()`, which instead checks the live decoder's `output_type` ClassVar.
    """

    output_type: FeatureType | None = None
    input_feature: dict | None = None
    output_feature: dict | None = None

    def verify_report(self, n2o) -> VerificationReport:
        """Check declared input/output specs across every pipeline boundary before `n2o.run()`.

        Walks signal -> decoder -> command -> robot.arm/hand. See `n2o.command.verify.verify`
        for the check logic — this is a convenience method so `n2o.command_config.
        verify_report(n2o)` works without `N2O` needing its own wrapper method.
        """
        from .verify import verify

        return verify(n2o, command_config=self)
