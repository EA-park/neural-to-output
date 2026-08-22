from abc import ABC, abstractmethod
from typing import ClassVar

from .config import DecoderConfig, FeatureType


class Decoder(ABC):
    """Base interface for translating a raw signal sample into a command."""

    input_spec: ClassVar[dict | None] = None
    """Shape/dtype contract for `decode()`'s `signal` argument. None means not yet decided.
    Checked against the signal source's `output_spec` by `CommandConfig.verify_report()`."""

    output_spec: ClassVar[dict | None] = None
    """Shape/key contract for the command `decode()` returns. None means not yet decided.
    Checked against the command (or robot) `input_spec` by `CommandConfig.verify_report()`."""

    output_type: ClassVar[FeatureType | None] = None
    """Semantic type of the decoded command, read by `N2O.run()`: `FeatureType.ACTION` routes
    through `Command.translate()` to `robot.arm/hand.move()`; `FeatureType.LANGUAGE` routes
    through `N2O.controller.act()` instead. Must be one of these two — `run()` raises if it
    isn't set."""

    config: DecoderConfig
    """Instance-level (not a ClassVar) metadata about this decoder — set in `__init__` by each
    concrete decoder, e.g. `self.config = DecoderConfig(type=DecoderType.CLASSIFICATION)`. A
    decoder wrapping more than one internal model may set `config.type` to a
    `tuple[DecoderType, ...]` instead of a single `DecoderType` — see `n2o.decoder.DecoderConfig`.
    `Command.translate()` reads `decoder.config.type` to decide how to interpret `decoded_signal`."""

    @abstractmethod
    def decode(self, signal):
        """Return a command derived from a raw signal sample."""
        raise NotImplementedError

    def __call__(self, signal):
        """Shorthand for `decode(signal)` — lets a `Decoder` instance be called like a function."""
        return self.decode(signal)
