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
    """Instance-level (not a ClassVar) metadata about this decoder — set in `__init__`, e.g.
    `Decoder(DecoderConfig(type=DecoderType.CLASSIFICATION))`. A decoder wrapping more than
    one internal model may set `config.type` to a `tuple[DecoderType, ...]` instead of a
    single `DecoderType` — see `n2o.decoder.DecoderConfig`. `Command.translate()` reads
    `decoder.config.type` to decide how to interpret `decoded_signal`; `prepare()` (below)
    reads `config.preprocessing_kwargs`/`config.windowing_kwargs` -- the single source of
    truth for how this decoder expects a raw recording prepared, instead of a second,
    separate copy of the same facts living directly on `self`."""

    def __init__(self, config: DecoderConfig | None = None):
        """`config.preprocessing_kwargs`/`config.windowing_kwargs` record how *this*
        decoder expects a raw recording prepared before `decode()` can run on it (e.g.
        the recipe its weights were trained with, for a pretrained checkpoint) — set
        them there and call `prepare(raw_dataset)` instead of calling
        `preprocess()`/`window()` directly with the right kwargs remembered by hand.
        `config.windowing_kwargs` has no dataset-agnostic default (see `window()`), so
        it's `None` unless a subclass's caller sets it. `config` defaults to a fresh,
        all-unset `DecoderConfig()` when omitted.

        `cycle` (default `1`) is how many times `N2O.run()` loops -- read via
        `getattr(self.decoder, "cycle", 1)`, not passed to `run()` itself. A subclass
        meant to drive a static offline recording through several *different* results
        per demo (e.g. `OfnerEEGNet`, which sets `self.cycle = 3`) should raise this;
        see `__call__()` for what it actually changes."""
        self.config = config or DecoderConfig()
        self.cycle = 1
        self._prepared_windows = None
        self._window_index = 0

    @abstractmethod
    def decode(self, signal):
        """Return a command derived from a raw signal sample."""
        raise NotImplementedError

    @abstractmethod
    def preprocess(self, raw_dataset, **kwargs):
        """Filter/normalize `raw_dataset` in place, ready for `window()`.

        How this is done depends on the task type, not just the signal — a
        `Classification`/`Regression` subclass implements this, not `Decoder` itself.
        """
        raise NotImplementedError

    @abstractmethod
    def window(self, raw_dataset, **kwargs):
        """Cut `raw_dataset` into decode()-ready windows.

        A discrete per-trial label (`Classification`) and a continuously-changing
        target (`Regression`) need different windowing shapes — one window per event
        vs. overlapping sliding windows — so this has no shared default either.
        """
        raise NotImplementedError

    def prepare(self, raw_dataset):
        """`preprocess()` then `window()` `raw_dataset`, using this decoder's own
        `config.preprocessing_kwargs`/`config.windowing_kwargs` -- so callers don't
        have to remember and re-apply those numbers by hand. Returns the windowed
        dataset.

        Requires `config.windowing_kwargs` (at least whatever `window()`'s
        task-specific offset/size argument is) to have been set at construction —
        there's no dataset-agnostic default for it.
        """
        if self.config.windowing_kwargs is None:
            raise ValueError(
                "prepare() needs config.windowing_kwargs set at construction -- "
                "there's no dataset-agnostic default for it, see Decoder.window()"
            )
        self.preprocess(raw_dataset, **self.config.preprocessing_kwargs)
        return self.window(raw_dataset, **self.config.windowing_kwargs)

    def __call__(self, signal):
        """Shorthand for `decode(signal)` — lets a `Decoder` instance be called like a
        function. `signal` is usually already decode()-ready (e.g. one window's data
        array), but if it's still a raw, unwindowed recording — what
        `DatasetLoader.read()`/`StreamLoader.read()` return, detected the same way
        `moabb_entry.py`/the example notebooks read a raw recording's channels
        (`dataset.datasets[0].raw`) — `prepare()` it, once (cached in
        `self._prepared_windows` — a raw recording is a bounded offline dataset in
        this project, see `n2o.signal.dataset`, so nothing legitimately changes it
        between calls; re-preparing every call would just redo the same expensive
        filter/window work for the same result), then pick a window from it:

        - `self.cycle <= 1` (the default): always the *most recent* window, mirroring
          a live stream where only the newest chunk matters.
        - `self.cycle > 1`: one of `self.cycle` windows spread evenly across the
          prepared set, advancing to the next on every call (wrapping around) — so a
          decoder meant to demo several different results per `N2O.run()` cycle (e.g.
          `OfnerEEGNet`, `self.cycle = 3`) doesn't decode the same window every time.
        """
        if hasattr(signal, "datasets") and hasattr(signal.datasets[0], "raw"):
            if self._prepared_windows is None:
                self._prepared_windows = self.prepare(signal)
            windows = self._prepared_windows
            if self.cycle <= 1:
                signal = windows[-1][0]
            else:
                step = max(1, len(windows) // self.cycle)
                index = (self._window_index * step) % len(windows)
                self._window_index += 1
                signal = windows[index][0]
        return self.decode(signal)
