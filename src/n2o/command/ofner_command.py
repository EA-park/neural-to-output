from __future__ import annotations

from .command import Command

LABEL_TO_GESTURE = {
    "rest": ("hand", "open_hand"),
    "right_elbow_extension": ("hand", "close_hand"),
    "right_elbow_flexion": ("hand", "clench_hand"),
    "right_hand_close": ("hand", "victory"),
    "right_hand_open": ("hand", "index_pointing"),
    "right_pronation": ("hand", "nonono"),
    "right_supination": ("hand", "perfect"),
}
"""Maps each of `OfnerEEGNet`'s seven raw labels to a `(part, gesture)` pair --
`part` is always `"hand"` here (the arm stays `None` -- see below), `gesture` is one
of the seven names `n2o.robot.simulation.amazing_hand.HAND_ACTION_POSE` (and
`n2o.robot.hand.amazing_hand_real.AmazingHandRealController`, which reuses that same
table) defines: `open_hand`/`close_hand`/`clench_hand`/`victory`/`index_pointing`/
`nonono`/`perfect`, ported from `AmazingHand-main/PythonExample/AmazingHand_Demo.py`'s
gesture functions. All seven labels route to the hand -- none of Ofner2017's labels
map to the arm anymore, so `robot.arm` (if assigned) never actually moves; this is a
placeholder mapping, arbitrarily assigned label-to-gesture, not a considered design --
edit it to whatever mapping you actually want."""


class OfnerCommand(Command):
    """Maps `OfnerEEGNet`'s raw predicted class index to one hand gesture.

    `decoded_signal` is the raw class index `OfnerEEGNet.decode()` returns (an
    `int`) -- resolved back to its label string via `decoder.config.labels`
    (populated automatically by `Classification.window()`, see `n2o.decoder.
    Classification`), then looked up in `LABEL_TO_GESTURE`.
    """

    def translate(self, decoder, decoded_signal):
        label = decoder.config.labels[decoded_signal]
        part, gesture = LABEL_TO_GESTURE[label]
        command = {"type": decoder.config.type, "arm": None, "hand": None}
        command[part] = gesture
        return command
