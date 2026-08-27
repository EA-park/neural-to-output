from __future__ import annotations

from pathlib import Path

import torch

from ..braindecode_entry import BraindecodeDecoder

_CHECKPOINT_PATH = Path(__file__).parent / "checkpoint.pt"

_N_CHANS = 61
_N_OUTPUTS = 7
_N_TIMES = 1536  # 3.0s @ 512Hz -- Ofner2017's own cue-relative interval ([0, 3])
_WINDOWING_KWARGS = {"start_offset_sec": 0.0, "stop_offset_sec": 0.0}
_LABELS = [
    "rest",
    "right_elbow_extension",
    "right_elbow_flexion",
    "right_hand_close",
    "right_hand_open",
    "right_pronation",
    "right_supination",
]


class NewOfnerEEGNet(BraindecodeDecoder):
    """EEGNet trained on moabb/braindecode's Ofner2017 (61 EEG channels, 7-class
    upper-limb motor imagery: rest + elbow flexion/extension + forearm pronation/
    supination + hand open/close).

    No public pretrained checkpoint exists for this dataset -- checked the Hugging
    Face Hub for both models and datasets matching "Ofner"/"Ofner2017"/"upper limb
    EEG"/"Graz upper limb", zero results -- so this repo bundles its own, trained
    locally on subject 1's imagined-movement session (10 runs; runs 8-9 held out for
    validation, the rest used for training; see `checkpoint.pt` next to this file).

    Held-out validation accuracy: **100%** (7-class, chance = 14.3%). Take this with a
    grain of salt rather than as a clean benchmark result -- verified the per-run trial
    order isn't a fixed repeating sequence (so it isn't literally memorizing trial
    position), but 100% is still unusually high for imagined-only motor imagery on a
    single subject/session; it may reflect genuinely strong subject-specific signal,
    or residual non-cortical contamination (e.g. EMG bleed-through) the 4-38Hz
    bandpass doesn't fully remove, rather than pure cortical decoding. Good enough to
    exercise the pipeline end-to-end; not a claim this generalizes to another subject.

    ```python
    decoder = NewOfnerEEGNet()
    decoder.config.labels  # the 7 class names above, class-index ordered
    ```
    """

    def __init__(self):
        super().__init__(
            "EEGNet",
            n_chans=_N_CHANS,
            n_outputs=_N_OUTPUTS,
            n_times=_N_TIMES,
            windowing_kwargs=_WINDOWING_KWARGS,
        )
        state_dict = torch.load(_CHECKPOINT_PATH, map_location="cpu")
        self.model.load_state_dict(state_dict)
        self.config.labels = list(_LABELS)
        self.cycle = 3
        # Ofner2017 is a static recording -- read fresh via a plain DatasetLoader,
        # every N2O.run() cycle would otherwise decode the same last window (see
        # Decoder.__call__()). Cycling through 3 spread-out windows instead gives a
        # demo genuinely different results per cycle.
