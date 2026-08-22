from .base import SignalStream


class EEGStream(SignalStream):
    """Realtime EEG signal source (e.g. a live LSL/device connection)."""

    def read(self):
        raise NotImplementedError
