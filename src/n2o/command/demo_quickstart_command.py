from __future__ import annotations

from .command import Command

LABEL_TO_GESTURE = {
    "rest": "open_hand",
    "right_elbow_extension": "close_hand",
    "right_elbow_flexion": "clench_hand",
    "right_hand_close": "victory",
    "right_hand_open": "index_pointing",
    "right_pronation": "nonono",
    "right_supination": "perfect",
}
"""Maps each of `OfnerEEGNet`'s seven raw labels to one of
`n2o.robot.hand.AmazingHand.GESTURES`' named poses. Unlike `OfnerCommand.
LABEL_TO_GESTURE`, every label routes to `"hand"` -- no label maps to `"arm"` -- since
this variant targets `demos/quickstart.py`'s hardware setup, which only assigns
`n2o.robot.hand` (no `n2o.robot.arm`); an arm-routed gesture there would just be
silently skipped by `Robot.router()`. This is a placeholder mapping, arbitrarily
assigned label-to-gesture, not a considered design -- edit it to whatever mapping you
actually want."""


class OfnerHandCommand(Command):
    """Maps `OfnerEEGNet`'s raw predicted class index to one `AmazingHand` gesture.

    `decoded_signal` is the raw class index `OfnerEEGNet.decode()` returns (an
    `int`) -- resolved back to its label string via `decoder.config.labels`
    (populated automatically by `Classification.window()`, see `n2o.decoder.
    Classification`), then looked up in `LABEL_TO_GESTURE`. Lives in
    `demo_quickstart_command.py`, named for its one consumer, `demos/quickstart.py`,
    whose robot only has a hand assigned -- see `LABEL_TO_GESTURE`'s own docstring
    for why this differs from `OfnerCommand`.
    """

    def translate(self, decoder, decoded_signal):
        label = decoder.config.labels[decoded_signal]
        return {
            "type": decoder.config.type,
            "arm": None,
            "hand": LABEL_TO_GESTURE[label],
        }
