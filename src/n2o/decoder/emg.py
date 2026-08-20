from .base import Decoder


class EMGDecoder(Decoder):
    """Decoder for EMG signals."""

    def decode(self, signal):
        raise NotImplementedError
