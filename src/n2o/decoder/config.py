from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FeatureType(str, Enum):
    """Semantic type of a command flowing between `decoder` and `robot`."""

    SIGNAL = "SIGNAL"
    LANGUAGE = "LANGUAGE"  # a VLA-style instruction, routed through a Controller
    ACTION = "ACTION"  # a direct motor/action command, routed through Command to robot.arm/hand


class DecoderType(str, Enum):
    CLASSIFICATION = "CLASSIFICATION"
    REGRESSION = "REGRESSION"


@dataclass(slots=True)
class DecoderConfig:
    """Shape/task metadata for a decoder — how big its input is, what its output means.

    `type` is usually a single `DecoderType`, but a decoder wrapping more than one
    internal model (e.g. one classifier + one regressor) can set it to a
    `tuple[DecoderType, ...]` instead — `Command.translate()` branches on this to know
    whether `decoded_signal` is a single value or already split per sub-model.

    `input_feature`/`output_feature` describe sizes (input dimensionality; output class
    count for CLASSIFICATION, or regression target size for REGRESSION) — not yet a
    finalized shape, may change once real decoders exist.
    """

    type: DecoderType | tuple[DecoderType, ...] | None = None
    input_feature: int | None = None
    output_feature: int | None = None
