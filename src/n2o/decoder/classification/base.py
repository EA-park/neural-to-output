from __future__ import annotations

from ..base import Decoder
from ..utils.preprocessing import bandpass_standardize
from ..utils.windowing import label_names, window_by_event


class Classification(Decoder):
    """Base for decoders that predict a discrete class label.

    Cuts one event-locked window per trial (`window_by_event()`) -- the natural
    windowing shape for a single per-trial label, as opposed to `Regression`'s
    continuous sliding windows. `decode()` stays abstract -- subclass this (e.g.
    `BraindecodeDecoder`) to wrap a real classifier.
    """

    def preprocess(self, raw_dataset, **kwargs):
        return bandpass_standardize(raw_dataset, **kwargs)

    def window(self, raw_dataset, **kwargs):
        """Cut `raw_dataset` into event-locked windows, and record the
        class-index-ordered label list on `self.config.labels` -- read off the
        windowed dataset's own event mapping (`label_names()`), not guessed or
        re-typed by a caller. Populated as a side effect of `window()`/`prepare()`
        finishing, so `Command.translate()` can read `decoder.config.labels` with no
        extra plumbing once decoding is set up.
        """
        windows = window_by_event(raw_dataset, **kwargs)
        self.config.labels = label_names(windows)
        return windows
