from abc import ABC, abstractmethod


class Decoder(ABC):
    """Base interface for translating a raw signal sample into a command."""

    @abstractmethod
    def decode(self, signal):
        """Return a command derived from a raw signal sample."""
        raise NotImplementedError
