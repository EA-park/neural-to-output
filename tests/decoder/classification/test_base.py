import pytest

from n2o.decoder import Classification, DecoderConfig, FeatureType


class _StubClassifier(Classification):
    output_type = FeatureType.ACTION

    def decode(self, signal):
        return 0


def test_classification_is_still_abstract_without_decode():
    with pytest.raises(TypeError):
        Classification()  # decode() unimplemented


def test_preprocess_drops_non_eeg_channels(synthetic_concat_dataset):
    # bandpass_standardize() picks EEG channels only -- proves Classification.preprocess()
    # actually delegates to it rather than being a no-op.
    decoder = _StubClassifier()
    decoder.preprocess(synthetic_concat_dataset)
    assert synthetic_concat_dataset.datasets[0].raw.get_data().shape[0] == 3


def test_window_cuts_one_window_per_trial(synthetic_concat_dataset):
    decoder = _StubClassifier()
    windows = decoder.window(synthetic_concat_dataset)
    assert len(windows) == 2


def test_window_populates_config_labels(synthetic_concat_dataset):
    # fixture's annotations are ["left_hand", "right_hand"] -- window() should record
    # them on config.labels automatically, not just make them available via
    # label_names() for a caller to remember to call separately.
    decoder = _StubClassifier()
    assert decoder.config.labels is None
    decoder.window(synthetic_concat_dataset)
    assert decoder.config.labels == ["left_hand", "right_hand"]


def test_prepare_combines_preprocess_and_window(synthetic_concat_dataset):
    decoder = _StubClassifier(
        config=DecoderConfig(windowing_kwargs={"start_offset_sec": -0.5})
    )
    windows = decoder.prepare(synthetic_concat_dataset)
    X0, _y0, _crop = windows[0]
    assert X0.shape == (3, 250)  # EOG dropped, -0.5s start offset -> +50 samples
    assert decoder.config.labels == ["left_hand", "right_hand"]
