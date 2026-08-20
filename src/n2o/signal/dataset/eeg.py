from .base import SignalDataset


class EEG(SignalDataset):
    """Non-invasive (scalp) EEG signal source."""

    def read(self):
        raise NotImplementedError


class InvasiveEEG(SignalDataset):
    """Invasive (e.g. ECoG) EEG signal source."""

    def read(self):
        raise NotImplementedError
