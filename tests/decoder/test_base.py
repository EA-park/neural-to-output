import numpy as np

from n2o.decoder import Classification, DecoderConfig, FeatureType
from n2o.decoder.utils import window_by_event


class _RecordingClassifier(Classification):
    output_type = FeatureType.ACTION

    def __init__(self, config=None):
        super().__init__(config)
        self.received = []

    def decode(self, signal):
        self.received.append(signal)
        return 0


def test_call_passes_an_already_windowed_array_straight_to_decode():
    decoder = _RecordingClassifier()
    array = np.zeros((3, 200), dtype="float32")

    decoder(array)

    assert decoder.received == [array]
    assert decoder.config.labels is None  # window()/prepare() never ran


def test_call_prepares_a_raw_dataset_and_decodes_only_the_last_window(
    synthetic_concat_dataset,
):
    decoder = _RecordingClassifier(config=DecoderConfig(windowing_kwargs={}))

    decoder(synthetic_concat_dataset)

    assert len(decoder.received) == 1
    # config.labels only gets populated as a side effect of window() actually
    # running -- proves __call__ auto-prepared the raw dataset rather than passing
    # it straight to decode().
    assert decoder.config.labels == ["left_hand", "right_hand"]

    # the dataset was band-pass filtered in place by prepare() -- re-deriving windows
    # from it now and checking against the *last* one confirms decode() got the most
    # recent window, not the first.
    windows = window_by_event(synthetic_concat_dataset)
    assert len(windows) == 2
    np.testing.assert_array_equal(decoder.received[0], windows[-1][0])


def test_call_cycles_through_spread_out_windows_when_cycle_is_set(
    synthetic_concat_dataset,
):
    decoder = _RecordingClassifier(config=DecoderConfig(windowing_kwargs={}))
    decoder.cycle = 2  # fixture has exactly 2 windows -- one per cycle, no repeats

    for _ in range(2):
        decoder(synthetic_concat_dataset)

    windows = window_by_event(synthetic_concat_dataset)
    assert len(decoder.received) == 2
    np.testing.assert_array_equal(decoder.received[0], windows[0][0])
    np.testing.assert_array_equal(decoder.received[1], windows[1][0])


def test_call_wraps_around_after_exhausting_cycle_windows(synthetic_concat_dataset):
    decoder = _RecordingClassifier(config=DecoderConfig(windowing_kwargs={}))
    decoder.cycle = 2

    for _ in range(3):  # one more call than cycle -- should wrap back to window 0
        decoder(synthetic_concat_dataset)

    windows = window_by_event(synthetic_concat_dataset)
    np.testing.assert_array_equal(decoder.received[0], windows[0][0])
    np.testing.assert_array_equal(decoder.received[1], windows[1][0])
    np.testing.assert_array_equal(decoder.received[2], windows[0][0])


def test_call_prepares_the_raw_dataset_only_once_across_multiple_calls(
    synthetic_concat_dataset,
):
    decoder = _RecordingClassifier(config=DecoderConfig(windowing_kwargs={}))
    decoder.cycle = 2
    prepare_calls = []
    original_prepare = decoder.prepare
    decoder.prepare = lambda raw_dataset: (
        prepare_calls.append(1) or original_prepare(raw_dataset)
    )

    for _ in range(3):
        decoder(synthetic_concat_dataset)

    assert len(prepare_calls) == 1
