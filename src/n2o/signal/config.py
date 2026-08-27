from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SignalType(str, Enum):
    """Whether a signal source records inside (invasive) or outside (non-invasive) the body."""

    INVASIVE = "INVASIVE"
    NON_INVASIVE = "NON_INVASIVE"


@dataclass(slots=True)
class SignalConfig:
    """Acquisition-time metadata for a signal source (electrode layout, sample rate).

    Distinct from `DatasetLoader`/`StreamLoader`'s `output_spec` — that's the read()-shape
    contract `CommandConfig.verify_report()` checks; this is descriptive metadata about the
    recording setup.
    """

    num_electrode: int | None = None
    name: tuple[str, ...] | None = None
    hz: float | None = None
    type: SignalType | None = None
