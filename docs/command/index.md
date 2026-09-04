# Command

Documentation for translating a decoder's raw prediction into per-part robot actions.

## `Command`

[`Command`][n2o.command.command.Command] (in `n2o.command.command`) is a plain overridable class, not a declarative
config. Its default `translate()` assumes `decoded_signal` is already keyed by robot
part:

```python
class Command:
    def translate(self, decoder, decoded_signal):
        return decoded_signal  # {"type": ..., "arm": ..., "hand": ...}
```

Subclass and override `translate(self, decoder, decoded_signal)` whenever a decoder's
raw output needs real translation into that shape first — most decoders' raw output
isn't already `{"arm": ..., "hand": ...}`.

Each part's value is either a bare, self-describing name (`"grip"`) or an
`(ActionType, value)` tuple for values that aren't self-describing on their own (a
regression number/dict). [`ActionType`][n2o.command.command.ActionType] — `JOINT_ABSOLUTE`, `JOINT_RELATIVE`,
`CARTESIAN_ABSOLUTE`, `CARTESIAN_RELATIVE` — travels with the value, independent of the
decoder's own `DecoderType`.

**Keep a `Decoder` a plain predictor** (raw prediction out) and put the prediction →
per-part-action mapping in `Command` — that's the whole reason `Command` exists
separately.

## Shipped subclasses

A `Command` subclass is usually notebook-local, since it encodes one specific
decoder's raw output → one specific robot's parts. Three are shipped in `src/`:

- **[`GripSpreadCommand`][n2o.command.grip_spread.GripSpreadCommand]** (`n2o/command/grip_spread.py`) — maps `BNCI2014_001`'s four
  raw motor-imagery labels (`feet`/`left_hand`/`right_hand`/`tongue`) to [`AmazingHand`][n2o.robot.hand.amazing_hand_right.AmazingHand]'s
  four single-finger poses. Reusable by any decoder that predicts that same label set.
- **[`OfnerCommand`][n2o.command.ofner_command.OfnerCommand]** (`n2o/command/ofner_command.py`) — maps `OfnerEEGNet`'s seven raw
  labels to one arm-or-hand gesture each via `LABEL_TO_GESTURE` (resolving
  `decoder.config.labels[decoded_signal]` back to its label string first). Its current
  mapping is a placeholder, not a considered design — expect it to change.
- **[`OfnerHandCommand`][n2o.command.demo_quickstart_command.OfnerHandCommand]** (`n2o/command/demo_quickstart_command.py`,
  named for its one consumer, `demos/quickstart.py`) — the same seven `OfnerEEGNet`
  labels as `OfnerCommand`, but every label maps to an `AmazingHand` gesture only
  (never `"arm"`), since that script's robot only has a hand assigned. Also a
  placeholder mapping, not a considered design.

## `CommandConfig`: checking the pipeline before `run()`

[`CommandConfig`][n2o.command.config.CommandConfig] (in `n2o.command.config`) is a separate, declarative contract for the
`command` boundary, pairing with `Command` the same way `SignalConfig`/`DecoderConfig`
pair with `signal`/`decoder`:

```python
n2o.command_config.verify_report(n2o)
```

Walks `signal -> decoder -> command -> robot.arm/hand` and prints a match/mismatch/미정
table — there's no `N2O.verify()` method, call `verify_report()` directly.
`DecoderConfig.type` can be a `tuple[DecoderType, ...]` for a decoder wrapping more
than one internal model; `Command.translate()` reads `decoder.config.type` (an
instance attribute) to decide how to interpret `decoded_signal`.
