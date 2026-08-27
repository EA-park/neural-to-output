from abc import ABC, abstractmethod
from typing import ClassVar


class StreamLoader(ABC):
    """Base interface for a realtime (unbounded) signal source, e.g. a live device.

    Sibling to `DatasetLoader` rather than a subclass of it — mirrors the `mne.io.Raw`
    (bounded, offline) vs `mne_lsl.stream.StreamLSL` (unbounded, ring-buffered) split.
    """

    output_spec: ClassVar[dict | None] = None
    """Shape/dtype contract for what `read()` returns. None means not yet decided.
    Checked against the decoder's `input_spec` by `N2O.verify()`."""

    @abstractmethod
    def read(self):
        """Return the latest buffered signal chunk."""
        raise NotImplementedError
