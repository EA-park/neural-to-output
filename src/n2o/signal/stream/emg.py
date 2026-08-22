from .base import SignalStream


class EMGStream(SignalStream):
    """Realtime EMG signal source (e.g. a live device connection)."""

    def read(self):
        raise NotImplementedError
