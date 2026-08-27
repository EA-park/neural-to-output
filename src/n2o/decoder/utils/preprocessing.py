from __future__ import annotations


def _to_microvolts(data):
    return data * 1e6


def bandpass_standardize(
    concat_dataset,
    *,
    l_freq: float = 4.0,
    h_freq: float = 38.0,
    factor_new: float = 1e-3,
    init_block_size: int = 1000,
):
    """Bandpass-filter then exponential-moving-standardize `concat_dataset`, in place.

    Same steps `examples/01_explore_eeg_dataset.ipynb` walks through by hand: pick EEG
    channels only, convert V -> uV, bandpass `l_freq`-`h_freq` Hz (motor-imagery-relevant
    band by default), then standardize so amplitude scale doesn't dominate what a decoder
    sees. `concat_dataset` is a `braindecode.datasets.BaseConcatDataset` (what
    `braindecode.datasets.MOABBDataset(...)` returns) -- returned for chaining, but also
    mutated in place, matching `braindecode.preprocessing.preprocess()`'s own contract.
    """
    from braindecode.preprocessing import (
        Preprocessor,
        exponential_moving_standardize,
        preprocess,
    )

    preprocessors = [
        Preprocessor(
            "pick_types", apply_on_array=False, eeg=True, meg=False, stim=False
        ),
        Preprocessor(_to_microvolts),  # V -> uV
        Preprocessor("filter", apply_on_array=False, l_freq=l_freq, h_freq=h_freq),
        Preprocessor(
            exponential_moving_standardize,
            factor_new=factor_new,
            init_block_size=init_block_size,
        ),
    ]
    preprocess(concat_dataset, preprocessors)
    return concat_dataset
