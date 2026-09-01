from __future__ import annotations

import time
from pathlib import Path
from typing import ClassVar

from moabb.datasets.utils import dataset_list as MOABB_DATASET_LIST

from .library import DatasetInfo, DatasetLibraryEntry, register_dataset

# moabb.datasets.download.data_dl() calls pooch.retrieve() with retry_if_failed=0
# (no retries) and no way to override that from the outside (data_dl()/MOABBDataset()
# don't expose it) -- some of these datasets download many multi-hundred-MB files
# per subject over a plain, unauthenticated connection to a single host (zenodo.org
# for the BNCI/Ofner2017 upper-limb datasets), which empirically drops mid-transfer
# often enough to matter (seen live: ReadTimeout, then ChunkedEncodingError/
# IncompleteRead at 83% of one file). Retrying the whole `MOABBDataset(...)` call is
# safe, not wasteful -- pooch already skips any individual file that finished and
# was hashed on a previous attempt (see data_dl()'s `known_hash`/`destination.is_file()`
# check), so a retry only re-downloads the one file that actually failed.
_DOWNLOAD_RETRY_ATTEMPTS = 3
_DOWNLOAD_RETRY_BACKOFF_S = 5


class MoabbLibraryEntry(DatasetLibraryEntry):
    """Generic `DatasetLibraryEntry` backed by one `moabb.datasets` class.

    One dynamic subclass is created per class in `moabb.datasets.utils.dataset_list` (see
    `_register_all()` below) instead of hand-writing a file like the old `ofner2017.py` per
    dataset -- moabb already carries this information on each dataset class (`METADATA`,
    `interval`, `event_id`), so this adapter reshapes it into `DatasetInfo` rather than
    duplicating it by hand. `moabb_cls` is set per subclass by `_register_all()`, not by
    `__init__`, so every entry keeps the no-arg-construction contract `DatasetLoader`/
    `DATASET_LIBRARY` already rely on (`DATASET_LIBRARY[name]()`).
    """

    source: ClassVar[str] = "moabb"
    moabb_cls: ClassVar[type] = None

    def read(self, loader):
        """Load subject 1's raw recording -- nothing else.

        Preprocessing (`bandpass_standardize()`) and event-based windowing
        (`window_by_event()`) used to run here automatically; both now live in
        `n2o.decoder` instead (`preprocessing.py`/`windowing.py`) -- turning a raw
        recording into decoder-ready windows is the decoder's job, not the signal
        source's. `signal.read()` stays a plain loader: call those functions yourself
        on the result, the way `examples/01_explore_eeg_dataset.ipynb` does.
        """
        import mne
        import requests
        from braindecode.datasets import MOABBDataset

        # mne refuses to auto-create a download directory the user has explicitly
        # configured (MNE_DATA or a dataset-specific MNE_DATASETS_*_PATH override) --
        # it only auto-creates its own unconfigured ~/mne_data default. If that
        # configured directory doesn't exist yet (e.g. after moving machines), create
        # it here rather than surfacing mne's raw FileNotFoundError.
        for key, value in mne.get_config().items():
            if key == "MNE_DATA" or key.endswith("_PATH"):
                Path(value).expanduser().mkdir(parents=True, exist_ok=True)

        instance = self.moabb_cls()
        subject_id = instance.subject_list[0]

        # Transient network failures only -- a real HTTPError (e.g. 404, the file
        # genuinely isn't there) isn't retried, since trying again wouldn't change
        # that.
        transient_errors = (
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.Timeout,
        )
        for attempt in range(_DOWNLOAD_RETRY_ATTEMPTS):
            try:
                return MOABBDataset(dataset_name=instance, subject_ids=[subject_id])
            except transient_errors as exc:
                if attempt == _DOWNLOAD_RETRY_ATTEMPTS - 1:
                    raise
                print(
                    f"다운로드 연결이 끊겼습니다 ({exc.__class__.__name__}) -- "
                    f"{_DOWNLOAD_RETRY_BACKOFF_S}초 후 재시도 "
                    f"({attempt + 2}/{_DOWNLOAD_RETRY_ATTEMPTS})"
                )
                time.sleep(_DOWNLOAD_RETRY_BACKOFF_S)

    def info(self) -> DatasetInfo:
        cls = self.moabb_cls
        instance = cls()
        meta = getattr(cls, "METADATA", None)

        data_range_sec = None
        interval = getattr(instance, "interval", None)
        if interval is not None and len(interval) == 2:
            data_range_sec = (float(interval[0]), float(interval[1]))

        metadata = {
            "moabb_class": cls.__name__,
            "paradigm": getattr(instance, "paradigm", None),
            "num_subjects": len(getattr(instance, "subject_list", None) or []),
            "event_ids": getattr(instance, "event_id", None),
        }

        num_channels = None
        source = cls.__name__
        if meta is not None:
            acquisition = meta.acquisition
            num_channels = acquisition.n_channels
            metadata["sampling_rate_hz"] = acquisition.sampling_rate
            metadata["channel_types"] = acquisition.channel_types
            metadata["montage"] = acquisition.montage
            metadata["reference"] = acquisition.reference

            experiment = meta.experiment
            metadata["n_classes"] = experiment.n_classes
            metadata["class_labels"] = experiment.class_labels
            metadata["study_design"] = experiment.study_design

            paradigm_specific = meta.paradigm_specific
            if paradigm_specific is not None:
                metadata["cue_duration_sec"] = paradigm_specific.cue_duration_s
                metadata["imagery_duration_sec"] = paradigm_specific.imagery_duration_s

            metadata["sessions_per_subject"] = meta.sessions_per_subject
            metadata["runs_per_session"] = meta.runs_per_session
            metadata["file_format"] = meta.file_format

            doc = meta.documentation
            if doc is not None:
                investigators = (
                    ", ".join(doc.investigators) if doc.investigators else None
                )
                header = investigators or cls.__name__
                if doc.publication_year:
                    header += f" ({doc.publication_year})"
                if doc.doi:
                    header += f" -- DOI {doc.doi}"
                source = header
                metadata["doi"] = doc.doi
                metadata["institution"] = doc.institution
                metadata["license"] = doc.license
                metadata["data_url"] = doc.data_url

        return DatasetInfo(
            source=source,
            cue_onset_sec=None,
            data_range_sec=data_range_sec,
            num_channels=num_channels,
            metadata=metadata,
        )


def _register_all():
    for moabb_cls in MOABB_DATASET_LIST:
        entry_cls = type(
            f"Moabb_{moabb_cls.__name__}",
            (MoabbLibraryEntry,),
            {"moabb_cls": moabb_cls},
        )
        register_dataset(moabb_cls.__name__)(entry_cls)


_register_all()
