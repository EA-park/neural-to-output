from n2o.decoder.utils.windowing import (
    expected_window_samples,
    label_names,
    window_by_event,
    window_by_sliding,
)


def test_window_by_event_makes_one_window_per_annotation(synthetic_concat_dataset):
    windows = window_by_event(synthetic_concat_dataset)
    assert len(windows) == 2


def test_window_by_event_stop_offset_zero_matches_annotation_duration(
    synthetic_concat_dataset,
):
    # fixture's trials are 2.0s long at 100Hz -> 200 samples with no offsets
    windows = window_by_event(synthetic_concat_dataset)
    X0, _y0, _crop = windows[0]
    assert X0.shape == (4, 200)


def test_window_by_event_start_offset_extends_the_window(synthetic_concat_dataset):
    # -0.5s start offset adds 0.5s = 50 samples at 100Hz
    windows = window_by_event(synthetic_concat_dataset, start_offset_sec=-0.5)
    X0, _y0, _crop = windows[0]
    assert X0.shape == (4, 250)


def test_expected_window_samples_matches_what_window_by_event_actually_produces(
    synthetic_concat_dataset,
):
    # cross-check against the real thing, for every offset combo window_by_event's
    # own tests use above -- expected_window_samples must predict it exactly, not
    # approximately, since it's used to build a model's fixed-shape layers.
    for start_offset_sec, stop_offset_sec in [(0.0, 0.0), (-0.5, 0.0), (0.0, 0.5)]:
        predicted = expected_window_samples(
            synthetic_concat_dataset,
            start_offset_sec=start_offset_sec,
            stop_offset_sec=stop_offset_sec,
        )
        windows = window_by_event(
            synthetic_concat_dataset,
            start_offset_sec=start_offset_sec,
            stop_offset_sec=stop_offset_sec,
        )
        X0, _y0, _crop = windows[0]
        assert predicted == X0.shape[1]


def test_label_names_reads_the_windows_own_event_mapping(synthetic_concat_dataset):
    # fixture's annotations are ["left_hand", "right_hand"] -- read back, not hardcoded
    windows = window_by_event(synthetic_concat_dataset)
    names = label_names(windows)
    assert names == ["left_hand", "right_hand"]
    assert all(isinstance(name, str) for name in names)


def test_window_by_sliding_ignores_event_boundaries(synthetic_concat_dataset):
    # fixture is a single continuous 20s/2000-sample recording -- sliding windows
    # should tile the whole thing, not just the two 2s annotated trials.
    windows = window_by_sliding(
        synthetic_concat_dataset, window_size_samples=200, window_stride_samples=100
    )
    # floor((2000 - 200) / 100) + 1
    assert len(windows) == 19


def test_window_by_sliding_windows_overlap_by_the_stride(synthetic_concat_dataset):
    windows = window_by_sliding(
        synthetic_concat_dataset, window_size_samples=200, window_stride_samples=100
    )
    X0, _y0, crop0 = windows[0]
    X1, _y1, crop1 = windows[1]
    assert X0.shape == X1.shape == (4, 200)
    assert crop1[1] - crop0[1] == 100  # start sample advances by exactly the stride
