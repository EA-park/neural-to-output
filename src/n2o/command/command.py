from enum import Enum


class ActionType(str, Enum):
    """Tags how to interpret a robot part's raw value when it isn't already a self-describing
    name (e.g. a raw regression number/dict). Travels alongside the value as an
    `(ActionType, value)` tuple — independent of the decoder's own `DecoderType`."""

    JOINT_ABSOLUTE = "JOINT_ABSOLUTE"
    JOINT_RELATIVE = "JOINT_RELATIVE"
    CARTESIAN_ABSOLUTE = "CARTESIAN_ABSOLUTE"
    CARTESIAN_RELATIVE = "CARTESIAN_RELATIVE"


class Command:
    """Base command-translation stage: turns a decoder's raw output into a per-robot-part
    command dict `N2O.run()` hands to `robot.arm.move()`/`robot.hand.move()`.

    The default `translate()` assumes `decoded_signal` is already keyed by robot part
    (`{"arm": ..., "hand": ...}`, e.g. a decoder wrapping independent per-part sub-models) —
    subclass and override `translate()` whenever a decoder's raw output needs real
    translation into that shape first (e.g. one classification label determining both
    parts at once).

    A part's resulting value is either a bare, already self-describing name (e.g. `"grip"`)
    or an `(ActionType, value)` tuple (a raw regression value isn't self-describing on its
    own, so it's paired with how to interpret it) — which shape a part gets is entirely up
    to whoever builds `decoded_signal` or overrides `translate()`.
    """

    def translate(self, decoder, decoded_signal):
        decoder_type = decoder.config.type
        command = {"type": decoder_type, "arm": None, "hand": None}
        if isinstance(decoder_type, tuple):
            for key, signal in decoded_signal.items():
                command[key] = signal
        else:
            command["arm"] = decoded_signal.get("arm")
            command["hand"] = decoded_signal.get("hand")
        return command
