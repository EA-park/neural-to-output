from __future__ import annotations

from ..base import Decoder
from ..utils.preprocessing import bandpass_standardize
from ..utils.windowing import window_by_sliding


class Regression(Decoder):
    """Base for decoders that predict a continuous target.

    Cuts overlapping fixed-length windows across the whole recording
    (`window_by_sliding()`) rather than one window per discrete event, since a
    regression target (e.g. a joint angle) changes continuously instead of being
    fixed per trial like `Classification`'s label. `decode()` stays abstract --
    subclass this to wrap a real regressor.
    """

    def preprocess(self, raw_dataset, **kwargs):
        return bandpass_standardize(raw_dataset, **kwargs)

    def window(self, raw_dataset, **kwargs):
        return window_by_sliding(raw_dataset, **kwargs)
