from __future__ import annotations

from .command import Command

LABEL_TO_GESTURE = {
    "feet": "pinky",
    "left_hand": "grip",
    "right_hand": "release",
    "tongue": "thumb",
}
"""Maps BNCI2014_001's four raw motor-imagery labels to `AmazingHand`'s four
single-finger poses -- see `GripSpreadCommand` below for why this mapping exists at
all (no real grip/release-labeled EEG dataset is bundled with this project)."""


class GripSpreadCommand(Command):
    """Maps a decoder's raw motor-imagery label to one of `AmazingHand`'s hand poses.

    `examples/04_hand_intent_classification_amazinghand.ipynb` uses this: no public
    EEG dataset labeled with real grip/release intent is bundled, so it reuses
    `BNCI2014_001`'s four motor-imagery labels (`feet`/`left_hand`/`right_hand`/
    `tongue`) as stand-ins, mapped via `LABEL_TO_GESTURE` to four single-finger poses
    the hand can actually demonstrate. A decoder trained on different labels needs a
    different `Command` subclass instead -- this one is specific to that label set.

    `decoded_signal` must be a raw label string key of `LABEL_TO_GESTURE`; the hand
    action it maps to is already a self-describing name (e.g. `"grip"`), so it travels
    bare rather than as an `(ActionType, value)` tuple.
    """

    def translate(self, decoder, decoded_signal):
        return {
            "type": decoder.config.type,
            "arm": None,
            "hand": LABEL_TO_GESTURE[decoded_signal],
        }
