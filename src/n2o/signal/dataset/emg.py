from .base import SignalDataset


class EMG(SignalDataset):
    """Electromyography (EMG) signal source."""

    def read(self):
        raise NotImplementedError
