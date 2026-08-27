import typing

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
