import mne
import numpy as np
import pandas as pd
import pytest
from braindecode.datasets import BaseConcatDataset, RawDataset


@pytest.fixture
def synthetic_concat_dataset():
    """A tiny braindecode `BaseConcatDataset` (3 EEG + 1 EOG channel, 2 annotated trials).

    Stands in for what `braindecode.datasets.MOABBDataset(...)` returns, without any
    network access -- real enough for `preprocessing`/`windowing` to run their actual
    mne/braindecode calls against.
    """
    sfreq = 100.0
    n_times = 2000  # 20s
    ch_names = ["EEG1", "EEG2", "EEG3", "EOG1"]
    ch_types = ["eeg", "eeg", "eeg", "eog"]
    info = mne.create_info(ch_names, sfreq, ch_types)
    rng = np.random.default_rng(0)
    data = rng.normal(size=(len(ch_names), n_times)) * 1e-5  # volts, EEG-ish scale
    raw = mne.io.RawArray(data, info, verbose=False)
    raw.set_annotations(
        mne.Annotations(
            onset=[5.0, 10.0],
            duration=[2.0, 2.0],
            description=["left_hand", "right_hand"],
        )
    )
    return BaseConcatDataset([RawDataset(raw, pd.Series({"subject": 1}))])
