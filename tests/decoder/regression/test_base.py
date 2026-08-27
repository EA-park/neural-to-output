import pytest

from n2o.decoder import DecoderConfig, FeatureType, Regression


class _StubRegressor(Regression):
    output_type = FeatureType.ACTION

    def decode(self, signal):
        return 0.0


def test_regression_is_still_abstract_without_decode():
    with pytest.raises(TypeError):
        Regression()  # decode() unimplemented


def test_preprocess_drops_non_eeg_channels(synthetic_concat_dataset):
    decoder = _StubRegressor()
    decoder.preprocess(synthetic_concat_dataset)
    assert synthetic_concat_dataset.datasets[0].raw.get_data().shape[0] == 3


def test_window_cuts_overlapping_windows_across_the_whole_recording(
    synthetic_concat_dataset,
):
    # unlike Classification.window(), this ignores the fixture's 2 annotated trials
    # entirely and tiles the full 2000-sample recording.
    decoder = _StubRegressor()
    windows = decoder.window(
        synthetic_concat_dataset, window_size_samples=200, window_stride_samples=100
    )
    assert len(windows) == 19


def test_window_does_not_populate_config_labels(synthetic_concat_dataset):
    # unlike Classification.window(), a continuous target has no discrete label list.
    decoder = _StubRegressor()
    decoder.window(
        synthetic_concat_dataset, window_size_samples=200, window_stride_samples=100
    )
    assert decoder.config.labels is None


def test_prepare_combines_preprocess_and_window(synthetic_concat_dataset):
    decoder = _StubRegressor(
        config=DecoderConfig(
            windowing_kwargs={"window_size_samples": 200, "window_stride_samples": 100}
        )
    )
    windows = decoder.prepare(synthetic_concat_dataset)
    X0, _y0, _crop = windows[0]
    assert X0.shape == (3, 200)  # EOG dropped by preprocess()
