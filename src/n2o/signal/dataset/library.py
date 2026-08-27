from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from .loader import DatasetLoader

DATASET_LIBRARY: dict[str, type[DatasetLibraryEntry]] = {}
"""Registry of named dataset libraries, populated by `@register_dataset("Name")`."""


@dataclass(slots=True, frozen=True)
class DatasetInfo:
    """Descriptive metadata about one dataset (a registered library entry, or a `path=`
    local recording described by a `write_metadata_template()`-generated template -- see
    `metadata_template.py`).

    `cue_onset_sec` and `data_range_sec` describe the cue-locked windowing question from
    the design discussion this answers: when a cue fires mid-recording, `data_range_sec`
    is how many seconds before/after that cue the dataset's authors intended a trial to
    span (sourced from the originating paper/benchmark -- not derived from `num_channels`
    or any decoder). Fields are all optional: a generic library adapter (see
    `moabb_entry.py`) may not have every field in structured form, and a freshly generated
    local template starts out entirely unfilled. `metadata` holds everything else the
    dataset publisher documents (subject count, sampling rate, event codes, license, ...)
    that doesn't fit the fields above.
    """

    source: str | None = None
    cue_onset_sec: float | None = None
    data_range_sec: tuple[float, float] | None = None
    num_channels: int | None = None
    metadata: dict = field(default_factory=dict)


def register_dataset(name: str):
    """Class decorator registering a `DatasetLibraryEntry` under `name` in `DATASET_LIBRARY`."""

    def decorator(cls: type[DatasetLibraryEntry]) -> type[DatasetLibraryEntry]:
        DATASET_LIBRARY[name] = cls
        return cls

    return decorator


class DatasetLibraryEntry:
    """Owns the fetch/parse logic for one named, registered public dataset (e.g. Ofner2017).

    `DatasetLoader` stays a thin dispatcher across `path=`/`name=` modes by delegating
    `name=`-mode reads here, instead of special-casing every dataset's file format itself.
    """

    source: ClassVar[str] = "custom"
    """Which library this entry came from (e.g. `"moabb"`) -- groups `DatasetLoader.library_tree()`."""

    def read(self, loader: DatasetLoader):
        raise NotImplementedError

    def info(self) -> DatasetInfo:
        """Describe this dataset: origin, cue timing, cue-relative data range, channels."""
        raise NotImplementedError
