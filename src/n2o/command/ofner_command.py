from __future__ import annotations

from .command import Command

LABEL_TO_GESTURE = {
    "rest": ("hand", "down"),
    "right_elbow_extension": ("arm", "up"),
    "right_elbow_flexion": ("hand", "down2"),
    "right_hand_close": ("hand", "up2"),
    "right_hand_open": ("hand", "down2"),
    "right_pronation": ("arm", "down"),
    "right_supination": ("hand", "perfect"),
}
"""Maps each of `OfnerEEGNet`'s seven raw labels to a `(part, gesture)` pair. A
`"hand"` gesture is one of the names `n2o.robot.hand.AmazingHand.GESTURES` defines:
`open_hand`/`clench_hand`/`victory`/`index_pointing`/`perfect`, ported from
`AmazingHand-main/PythonExample/AmazingHand_Demo.py`'s gesture functions.
`right_pronation`/`right_elbow_extension` route to `"arm"` instead, as the bare
gesture names `"down"`/`"up"` -- `n2o.robot.arm.SO101Arm.GESTURES` defines these two
(hand-captured absolute joint-degree poses -- see `SO101Arm`'s own docstring). Both
`GESTURES` tables are read the same way whether `Robot.router()` is driving
`ControllerType.SIMULATION` (via each part's `goal()`) or `ControllerType.
MOTOR_DRIVER` (via `move()`) -- there's only ever one gesture vocabulary per part now,
not a separate one per backend. This is a placeholder mapping, arbitrarily assigned
label-to-gesture, not a considered design -- edit it to whatever mapping you actually
want."""


class OfnerCommand(Command):
    """Maps `OfnerEEGNet`'s raw predicted class index to one hand or arm gesture.

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
