import typing

import requests

from n2o.signal.dataset import DATASET_LIBRARY, DatasetInfo, MoabbLibraryEntry


def test_every_moabb_dataset_class_registered():
    from moabb.datasets.utils import dataset_list

    assert len(DATASET_LIBRARY) == len(dataset_list)


def test_registered_entries_are_moabb_backed_with_source_moabb():
    entry_cls = DATASET_LIBRARY["Ofner2017"]
    assert issubclass(entry_cls, MoabbLibraryEntry)
    assert entry_cls.source == "moabb"
    assert entry_cls.moabb_cls.__name__ == "Ofner2017"


def test_entries_construct_with_no_args():
    # DatasetLoader/DATASET_LIBRARY dispatch always does `DATASET_LIBRARY[name]()`.
    entry = DATASET_LIBRARY["Ofner2017"]()
    assert isinstance(entry.info(), DatasetInfo)


def test_read_loads_subject_ones_raw_recording_only(monkeypatch):
    # preprocessing/windowing used to happen here too -- they've moved to n2o.decoder
    # (see n2o.decoder.preprocessing/.windowing), so read() should now just load raw data.
    class FakeMoabbDataset:
        subject_list: typing.ClassVar = [1, 2, 3]

    def fake_moabb_dataset_ctor(dataset_name, subject_ids):
        assert isinstance(dataset_name, FakeMoabbDataset)
        assert subject_ids == [1]
        return "raw_concat_dataset"

    monkeypatch.setattr("braindecode.datasets.MOABBDataset", fake_moabb_dataset_ctor)

    entry_cls = type(
        "FakeMoabbEntry", (MoabbLibraryEntry,), {"moabb_cls": FakeMoabbDataset}
    )
    result = entry_cls().read(loader=None)

    assert result == "raw_concat_dataset"


def _fake_entry_cls():
    class FakeMoabbDataset:
        subject_list: typing.ClassVar = [1]

    return type("FakeMoabbEntry", (MoabbLibraryEntry,), {"moabb_cls": FakeMoabbDataset})


def test_read_retries_transient_network_errors_then_succeeds(monkeypatch):
    monkeypatch.setattr("n2o.signal.dataset.moabb_entry.time.sleep", lambda _s: None)
    attempts = []

    def flaky_ctor(dataset_name, subject_ids):
        attempts.append(1)
        if len(attempts) < 3:
            raise requests.exceptions.ChunkedEncodingError("connection broken")
        return "raw_concat_dataset"

    monkeypatch.setattr("braindecode.datasets.MOABBDataset", flaky_ctor)

    result = _fake_entry_cls()().read(loader=None)

    assert result == "raw_concat_dataset"
    assert len(attempts) == 3


def test_read_gives_up_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("n2o.signal.dataset.moabb_entry.time.sleep", lambda _s: None)
    attempts = []

    def always_fails(dataset_name, subject_ids):
        attempts.append(1)
        raise requests.exceptions.ConnectionError("still broken")

    monkeypatch.setattr("braindecode.datasets.MOABBDataset", always_fails)

    try:
        _fake_entry_cls()().read(loader=None)
        raised = False
    except requests.exceptions.ConnectionError:
        raised = True

    assert raised
    assert len(attempts) == 3  # _DOWNLOAD_RETRY_ATTEMPTS, not retried forever


def test_read_does_not_retry_non_transient_errors(monkeypatch):
    monkeypatch.setattr("n2o.signal.dataset.moabb_entry.time.sleep", lambda _s: None)
    attempts = []

    def not_found(dataset_name, subject_ids):
        attempts.append(1)
        raise requests.exceptions.HTTPError("404 not found")

    monkeypatch.setattr("braindecode.datasets.MOABBDataset", not_found)

    try:
        _fake_entry_cls()().read(loader=None)
        raised = False
    except requests.exceptions.HTTPError:
        raised = True

    assert raised
    assert len(attempts) == 1  # not a transient error -- fails immediately
