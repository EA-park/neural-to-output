from __future__ import annotations

from dataclasses import dataclass, field
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

    `n_times`/`windowing_kwargs`/`preprocessing_kwargs` describe how a raw recording
    must be prepared before this decoder can `decode()` it -- the single source of
    truth `Decoder.prepare()` reads (see `n2o.decoder.Decoder`), instead of a decoder
    holding a second, separate copy of the same facts. `windowing_kwargs` has no
    dataset-agnostic default (same reasoning as `window_by_event()`'s own
    `start_offset_sec`), so it's `None` until explicitly set.

    `labels` is the class-index-ordered label list a `Classification` decoder's own
    `window()` fills in automatically once it has windowed data to read the mapping
    off of (via `label_names()`) -- `None` until then, and always `None` for a
    `Regression` decoder (a continuous target has no discrete label list).
    `Command.translate()` can read `decoder.config.labels[decoded_signal]` to turn a
    raw predicted class index back into its human-readable name.
    """

    type: DecoderType | tuple[DecoderType, ...] | None = None
    input_feature: int | None = None
    output_feature: int | None = None
    n_times: int | None = None
    windowing_kwargs: dict | None = None
    preprocessing_kwargs: dict = field(default_factory=dict)
    labels: list[str] | None = None
