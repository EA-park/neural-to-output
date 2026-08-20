from abc import ABC, abstractmethod


class SignalDataset(ABC):
    """Base interface for a source of raw signal samples."""

    @abstractmethod
    def read(self):
        """Return the next raw signal sample."""
        raise NotImplementedError
