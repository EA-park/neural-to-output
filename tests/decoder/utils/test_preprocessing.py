from n2o.decoder.utils.preprocessing import bandpass_standardize


def test_bandpass_standardize_drops_non_eeg_channels(synthetic_concat_dataset):
    bandpass_standardize(synthetic_concat_dataset)
    assert synthetic_concat_dataset.datasets[0].raw.ch_names == ["EEG1", "EEG2", "EEG3"]


def test_bandpass_standardize_returns_the_same_object(synthetic_concat_dataset):
    result = bandpass_standardize(synthetic_concat_dataset)
    assert result is synthetic_concat_dataset


def test_bandpass_standardize_rescales_data(synthetic_concat_dataset):
    raw_before = synthetic_concat_dataset.datasets[0].raw.get_data().copy()
    bandpass_standardize(synthetic_concat_dataset)
    raw_after = synthetic_concat_dataset.datasets[0].raw.get_data()

    # input was ~1e-5 (volts); exponential-moving-standardized output should be O(1)
    assert abs(raw_before).mean() < 1e-3
    assert abs(raw_after).mean() > 0.1
