from .base import Decoder


class EEGNet(Decoder):
    """EEGNet-based decoder for EEG signals."""

    def decode(self, signal):
        raise NotImplementedError
