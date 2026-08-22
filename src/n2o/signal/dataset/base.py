from abc import ABC, abstractmethod
from typing import ClassVar


class SignalDataset(ABC):
    """Base interface for a source of raw signal samples."""

    output_spec: ClassVar[dict | None] = None
    """Shape/dtype contract for what `read()` returns, e.g. {"channels": 59, "samples": 100}.
    None means not yet decided. Checked against the decoder's `input_spec` by `N2O.verify()`."""

    @abstractmethod
    def read(self):
        """Return the next raw signal sample."""
        raise NotImplementedError
