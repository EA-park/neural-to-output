from __future__ import annotations


def window_by_event(
    concat_dataset,
    *,
    start_offset_sec: float = 0.0,
    stop_offset_sec: float = 0.0,
):
    """Cut every trial in `concat_dataset` into one event-locked window.

    Each window spans `[event onset + start_offset_sec, trial end + stop_offset_sec]` --
    see `examples/01_explore_eeg_dataset.ipynb`'s windowing section for why a trial gets
    cut relative to its cue/event marker at all, rather than read as one continuous blob.

    There's no dataset-agnostic default for `start_offset_sec`: it's a property of the
    recording's own paradigm (see the moabb-sourced `DatasetInfo.data_range_sec[0]` from
    `n2o.signal.dataset.moabb_entry`), not something this function can guess.
    `stop_offset_sec` defaults to `0.0`, meaning "stop exactly at this trial's own
    annotated duration."
    """
    from braindecode.preprocessing import create_windows_from_events

    sfreq = concat_dataset.datasets[0].raw.info["sfreq"]
    return create_windows_from_events(
        concat_dataset,
        trial_start_offset_samples=round(start_offset_sec * sfreq),
        trial_stop_offset_samples=round(stop_offset_sec * sfreq),
        preload=True,
    )


def window_by_sliding(
    concat_dataset,
    *,
    window_size_samples: int,
    window_stride_samples: int,
    drop_last_window: bool = True,
):
    """Cut `concat_dataset` into overlapping fixed-length windows, independent of any
    per-trial event boundary.

    Unlike `window_by_event()` (one window per trial, for a single per-trial label),
    a regression target (e.g. a joint angle) changes continuously across a recording,
    so `Regression` decoders need many overlapping windows per trial instead of one --
    see `n2o.decoder.Regression`.
    """
    from braindecode.preprocessing import create_fixed_length_windows

    return create_fixed_length_windows(
        concat_dataset,
        window_size_samples=window_size_samples,
        window_stride_samples=window_stride_samples,
        drop_last_window=drop_last_window,
        preload=True,
    )


def expected_window_samples(
    raw_dataset, *, start_offset_sec: float, stop_offset_sec: float = 0.0
) -> int:
    """How many samples `window_by_event(raw_dataset, start_offset_sec=..., stop_offset_sec=...)`
    will produce per window, without actually running it.

    Exists so a `BraindecodeDecoder` can be built (which needs `n_times` up front, to
    construct its layers) *before* calling `prepare()` on the raw data -- otherwise
    you'd have to window first just to measure the result, then build the model, i.e.
    exactly the manual preprocess-then-window-then-decode order this project moved away
    from. Reads the same two facts `create_windows_from_events` derives a trial's window
    size from (its own annotated duration, and `raw_dataset`'s sample rate) instead of
    duplicating braindecode's windowing logic.
    """
    raw = raw_dataset.datasets[0].raw
    sfreq = raw.info["sfreq"]
    duration_s = raw.annotations.duration[0]
    return round((duration_s + stop_offset_sec - start_offset_sec) * sfreq)


def label_names(windows_dataset) -> list[str]:
    """Class-index-ordered label names for `windows_dataset`, from its own event mapping.

    `window_by_event()` (via `create_windows_from_events`) records a `{label: class
    index}` mapping on every window it cuts -- read that instead of a notebook/script
    hardcoding a guessed label list, which drifts the moment it's copied to a different
    dataset. Same principle as `start_offset_sec` having no dataset-agnostic default:
    the dataset's own config already knows this, so nothing here should re-guess it.
    """
    mapping = windows_dataset.datasets[0].window_kwargs[0][1]["mapping"]
    return [str(label) for label, _ in sorted(mapping.items(), key=lambda kv: kv[1])]
