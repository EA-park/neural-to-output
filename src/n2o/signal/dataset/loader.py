from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from . import metadata_template
from .library import DATASET_LIBRARY, DatasetInfo


class DatasetLoader:
    """Loads a bounded, offline recording (e.g. a saved file).

    Exactly one of `path` (a local folder) or `name` (a registered dataset library, e.g.
    `"Ofner2017"`) must be given; `name` is resolved through `DATASET_LIBRARY` (see
    `list_libraries()`). `path=` mode requires a `dataset_info.py` metadata file to
    already exist inside `path` -- construction itself raises `FileNotFoundError` if it
    doesn't. Generating that file is a separate, explicit step: call
    `n2o.signal.dataset.write_metadata_template(path)` (writes a blank, hand-fillable
    template you then edit and place in the recording folder yourself -- see
    `metadata_template.py`), *before* constructing a `DatasetLoader` for it.
    """

    output_spec: ClassVar[dict | None] = None
    """Shape/dtype contract for what `read()` returns, e.g. {"channels": 59, "samples": 100}.
    None means not yet decided. Checked against the decoder's `input_spec` by `N2O.verify()`."""

    def __init__(
        self,
        *,
        path: str | Path | None = None,
        name: str | None = None,
    ):
        if (path is None) == (name is None):
            raise ValueError("specify exactly one of `path` or `name`")
        if name is not None and name not in DATASET_LIBRARY:
            raise ValueError(
                f"unknown dataset library {name!r}; see DatasetLoader.list_libraries()"
            )
        self.path = Path(path) if path is not None else None
        self.name = name
        if (
            self.path is not None
            and not metadata_template.metadata_path(self.path).exists()
        ):
            raise FileNotFoundError(
                f"no metadata file at {metadata_template.metadata_path(self.path)}; "
                "call n2o.signal.dataset.write_metadata_template(path) to create one, "
                "fill it in, then construct DatasetLoader again"
            )

    def read(self):
        """Return this dataset's raw recording -- not preprocessed, not windowed.

        `name=` mode resolves through the registered library entry (for the moabb-backed
        ones -- see `moabb_entry.py` -- this loads subject 1's raw recording and nothing
        else). Turning that into decoder-ready windows is `n2o.decoder`'s job now, not
        `signal`'s: see `n2o.decoder.bandpass_standardize()`/`.window_by_event()`.

        `path=` mode has no registry entry to load from, so it's still an interface-only
        stub (`raise NotImplementedError`) here.
        """
        if self.name is not None:
            return DATASET_LIBRARY[self.name]().read(self)
        raise NotImplementedError

    def info(self) -> DatasetInfo:
        """Describe this dataset: origin, cue timing, cue-relative data range, channels.

        `name=` mode resolves through the registered library entry; `path=` mode reads the
        `dataset_info.py` file `__init__` already confirmed exists in `path` -- see
        `metadata_template.py`.
        """
        if self.name is not None:
            return DATASET_LIBRARY[self.name]().info()
        return metadata_template.load(self.path)

    @staticmethod
    def list_libraries() -> list[str]:
        """Names of registered dataset libraries, e.g. `["Ofner2017"]`."""
        return sorted(DATASET_LIBRARY)

    @staticmethod
    def library_tree(
        *, to_file: str | Path | None = None, inline_limit: int = 30
    ) -> str:
        """Render the registry as a tree grouped by source (e.g. `"moabb"`).

        A source like moabb registers hundreds of entries -- dumping that straight to a
        terminal is unusable, so past `inline_limit` this raises unless `to_file` names a
        path (e.g. a `.md` file) to write the tree to instead of returning it inline.
        """
        groups: dict[str, list[str]] = {}
        for entry_name, entry_cls in DATASET_LIBRARY.items():
            groups.setdefault(entry_cls.source, []).append(entry_name)

        lines = []
        for source in sorted(groups):
            names = sorted(groups[source])
            lines.append(f"{source} ({len(names)})")
            for i, name in enumerate(names):
                branch = "└── " if i == len(names) - 1 else "├── "
                lines.append(f"{branch}{name}")
        tree = "\n".join(lines)

        if to_file is not None:
            Path(to_file).write_text(tree)
            return f"{len(DATASET_LIBRARY)}개 데이터셋 목록을 {to_file}에 저장했습니다."
        if len(DATASET_LIBRARY) > inline_limit:
            raise ValueError(
                f"{len(DATASET_LIBRARY)} registered datasets exceeds inline_limit="
                f'{inline_limit}; pass to_file="library.md" to write the tree out instead'
            )
        return tree
